"""Fusion live data service — fetches real-time probe readings and history
directly from Apex Fusion, no local agent required."""

import json
import logging
import re
from typing import Optional, Any
from datetime import datetime, timezone

import requests

from app.database import AsyncSession, get_db
from app.models.tenant import TenantConfig
from sqlalchemy import select

log = logging.getLogger("reefmind.fusion.live")

FUSION_BASE = "https://apexfusion.com"

# Probe type mapping for display names
PROBE_DISPLAY_NAMES = {
    "base_Temp": "Temperature",
    "base_pH": "pH",
    "base_pH2": "CARXpH",
    "base_ORP": "ORP",
    "base_Cond": "Salinity",
}
PROBE_UNITS = {
    "Temp": "°F",
    "pH": "pH",
    "ORP": "mV",
    "Cond": "µS",
    "Salinity": "PPT",
}


class FusionLiveError(Exception):
    """Raised when Fusion live data fetch fails."""
    pass


class FusionLiveClient:
    """Lightweight session to Fusion for live data."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ReefMind/1.0",
        })
        self.csrf: Optional[str] = None

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Any:
        url = f"{FUSION_BASE}{path}"
        headers = {}
        if self.csrf:
            headers["csrf-token"] = self.csrf
        resp = self._session.get(url, headers=headers, timeout=30)
        if resp.status_code == 401:
            self.csrf = None
            raise FusionLiveError("Session expired — re-login required")
        resp.raise_for_status()
        return resp

    def _post(self, path: str, data: dict) -> Any:
        url = f"{FUSION_BASE}{path}"
        headers = {"Content-Type": "application/json"}
        if self.csrf:
            headers["csrf-token"] = self.csrf
        resp = self._session.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code == 401:
            self.csrf = None
            raise FusionLiveError("Session expired — re-login required")
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Log in to Apex Fusion."""
        log.info("Fetching CSRF token from Fusion...")
        resp = self._get("/")
        html = resp.text
        m = re.search(r'csrf-token"\s+content="([^"]+)"', html)
        if not m:
            raise FusionLiveError("Could not find CSRF token")
        self.csrf = m.group(1)

        log.info("Logging into Fusion as %s...", self.username)
        resp = self._post("/login", {
            "username": self.username,
            "password": self.password,
            "remember_me": True,
        })
        data = resp.json()
        if "redirect" not in data:
            raise FusionLiveError(
                f"Login failed — unexpected response: {json.dumps(data)[:200]}"
            )
        log.info("Login succeeded")

    # ------------------------------------------------------------------
    # Live readings
    # ------------------------------------------------------------------

    def get_live_readings(self, apex_id: str) -> list[dict]:
        """Fetch current probe readings from Fusion's live status.

        Returns a list matching the telemetry/summary format:
          {probe_name, probe_type, unit, value, time}
        """
        detail = self._get(f"/api/apex/{apex_id}").json()
        status_inputs = detail.get("status", {}).get("inputs", [])
        config_inputs = detail.get("config", {}).get("inputs", [])
        now = datetime.now(timezone.utc).isoformat()

        # Build config lookup to get probe names/types
        config_map = {}
        for inp in config_inputs:
            did = inp.get("did", "")
            config_map[did] = {
                "name": inp.get("name", did),
                "type": inp.get("type", "Unknown"),
            }

        readings = []
        for inp in status_inputs:
            did = inp.get("did", "")
            value = inp.get("value")
            if value is None:
                continue

            cfg = config_map.get(did, {})
            pname = cfg.get("name", did)
            ptype = cfg.get("type", "Unknown")

            # Map to cleaner display name
            display_name = PROBE_DISPLAY_NAMES.get(did, pname)

            # Only include actual sensor probes (Temp, pH, ORP, Cond)
            # Skip power/amps/energy/pwr meters
            sensor_types = {"Temp", "pH", "ORP", "Cond", "Salinity"}
            base_type = ptype
            if did.startswith("Tmp"):
                base_type = "Temp"
            elif did.startswith("pH"):
                base_type = "pH"
            elif did.startswith("ORP"):
                base_type = "ORP"
            elif did.startswith("Sal"):
                base_type = "Salinity"

            if base_type not in sensor_types:
                continue

            # Cast value to float if possible
            try:
                val = float(value)
            except (ValueError, TypeError):
                continue

            readings.append({
                "probe_name": display_name,
                "probe_type": base_type,
                "unit": PROBE_UNITS.get(base_type, "raw"),
                "value": val,
                "time": now,
                "did": did,
            })

        return readings

    def get_probe_history(self, apex_id: str, probe_did: str, hours: int = 6) -> list[dict]:
        """Fetch recent probe history from Fusion ilog.

        Returns a list compatible with telemetry/:probe format:
          {time, probe_name, probe_type, unit, value}
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Fetch ilog — use days param that maps to requested hours
        days = max(1, hours // 24 + 1)
        resp = self._get(f"/api/apex/{apex_id}/ilog?days={days}")
        data = resp.json()
        # ilog returns a flat list of {date, inputs: [{did, value}]}
        items = data if isinstance(data, list) else data.get("ilog", data.get("items", []))

        history = []
        for item in items:
            entry_time = item.get("date", "")
            if entry_time:
                try:
                    et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                    age_hours = (now - et).total_seconds() / 3600
                    if age_hours > hours:
                        continue
                except (ValueError, AttributeError):
                    pass

            inputs = item.get("inputs", [])
            for inp in inputs:
                if inp.get("did") == probe_did:
                    try:
                        val = float(inp.get("value", 0))
                    except (ValueError, TypeError):
                        continue
                    history.append({
                        "time": entry_time,
                        "probe_name": probe_did,
                        "probe_type": "unknown",
                        "unit": "raw",
                        "value": val,
                    })
                    break

        return history

    def get_all_outlet_states(self, apex_id: str) -> list[dict]:
        """Fetch current outlet states from Fusion."""
        detail = self._get(f"/api/apex/{apex_id}").json()
        config_outputs = detail.get("config", {}).get("outputs", [])
        status_outputs_map = {}
        for out in detail.get("status", {}).get("outputs", []):
            status_outputs_map[out.get("did", "")] = out.get("status", [])

        outlets = []
        for out in config_outputs:
            state_arr = status_outputs_map.get(out.get("did", ""), [])
            state = state_arr[0] if isinstance(state_arr, list) and len(state_arr) > 0 else ""
            outlets.append({
                "did": out.get("did", ""),
                "name": out.get("name", ""),
                "type": out.get("type", ""),
                "state": state,
            })
        return outlets

    def get_mlog(self, apex_id: str, days: int = 365) -> list[dict]:
        """Fetch water test results from Fusion mlog API.
        
        Returns: list of {type, value, date}
        """
        resp = self._get(f"/api/apex/{apex_id}/mlog?days={days}")
        return resp.json()

    def get_notes(self, apex_id: str, date_str: str = "",
                  page: int = 1, per_page: int = 200) -> list:
        """Fetch tank notes from Fusion notes API.
        
        Returns: [metadata, notes_list]
        """
        import time
        ts = int(time.time() * 1000)
        url = f"/api/apex/{apex_id}/notes?page={page}&per_page={per_page}&_={ts}"
        if date_str:
            url += f"&date={date_str}"
        resp = self._get(url)
        return resp.json()

    def get_all_notes(self, apex_id: str, days: int = 30) -> list[dict]:
        """Fetch all notes from the last N days, handling pagination.
        
        per_page=100 per Fusion API limits (200 causes 400 Bad Request).
        Returns: flat list of note dicts (merged from paginated responses).
        """
        from datetime import datetime, timedelta
        page = 1
        all_notes = []
        target_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        while True:
            result = self.get_notes(apex_id, date_str=target_date,
                                    page=page, per_page=100)
            # Result is [metadata_dict, notes_array]
            if not result or len(result) < 2:
                break
            notes = result[1] if isinstance(result[1], list) else []
            if not notes:
                break
            all_notes.extend(notes)
            if len(notes) < 100:
                break  # last page
            page += 1
        return all_notes

    def close(self):
        self._session.close()

    def get_controller_info(self, apex_id: str) -> dict:
        """Fetch controller hardware, software, serial, timezone from Fusion."""
        detail = self._get(f"/api/apex/{apex_id}").json()
        ctrl = detail.get("controller", {}) or {}
        return {
            "hardware": ctrl.get("hardware", ""),
            "software": ctrl.get("software", ""),
            "serial": ctrl.get("serial", ""),
            "timezone": ctrl.get("timezone", ""),
            "name": ctrl.get("name", ""),
        }


# ------------------------------------------------------------------
# High-level helpers (called by router)
# ------------------------------------------------------------------

async def load_tenant_config(tenant_id: str, db: AsyncSession) -> TenantConfig:
    """Load tenant config from DB, raise if Fusion not configured."""
    import uuid
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise FusionLiveError("Invalid tenant ID")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tid)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise FusionLiveError("Tenant configuration not found")

    if not config.fusion_user or not config.fusion_pass:
        raise FusionLiveError("Fusion not configured — go to Settings to connect")

    if not config.fusion_apex_id:
        raise FusionLiveError("Fusion controller not discovered — run Discovery in Settings")

    return config


def fetch_live_readings(config: TenantConfig) -> list[dict]:
    """Fetch live probe readings from Fusion for a configured tenant.

    Args:
        config: TenantConfig with fusion_user, fusion_pass, fusion_apex_id

    Returns: list of {probe_name, probe_type, unit, value, time}
    """
    client = FusionLiveClient(config.fusion_user, config.fusion_pass)
    try:
        client.login()
        readings = client.get_live_readings(config.fusion_apex_id)
        return readings
    except requests.exceptions.RequestException as e:
        raise FusionLiveError(f"Cannot reach Apex Fusion: {e}")
    finally:
        client.close()


def fetch_probe_history(config: TenantConfig, probe_did: str, hours: int = 6) -> list[dict]:
    """Fetch probe history from Fusion ilog.

    Args:
        config: TenantConfig with fusion_user, fusion_pass, fusion_apex_id
        probe_did: The probe's 'did' field (e.g. 'base_Temp')
        hours: How many hours of history to return

    Returns: list of {time, probe_name, probe_type, unit, value}
    """
    client = FusionLiveClient(config.fusion_user, config.fusion_pass)
    try:
        client.login()
        history = client.get_probe_history(config.fusion_apex_id, probe_did, hours=hours)
        return history
    except requests.exceptions.RequestException as e:
        raise FusionLiveError(f"Cannot reach Apex Fusion: {e}")
    finally:
        client.close()


def fetch_outlet_states(config: TenantConfig) -> list[dict]:
    """Fetch current outlet states from Fusion.

    Args:
        config: TenantConfig with fusion_user, fusion_pass, fusion_apex_id

    Returns: list of {did, name, type, state}
    """
    client = FusionLiveClient(config.fusion_user, config.fusion_pass)
    try:
        client.login()
        outlets = client.get_all_outlet_states(config.fusion_apex_id)
        return outlets
    except requests.exceptions.RequestException as e:
        raise FusionLiveError(f"Cannot reach Apex Fusion: {e}")
    finally:
        client.close()
