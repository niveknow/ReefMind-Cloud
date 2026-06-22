"""Fusion API discovery service for ReefMind cloud.

Wraps apex_fusion_client to discover Apex controller metadata,
probes, and outlets during user onboarding.
"""
import json
import logging
from typing import Optional, Any

# Import the Fusion client — in production this will be pip-installed
# For now we copy the relevant parts inline
import requests

log = logging.getLogger("reefmind.fusion")

FUSION_BASE = "https://apexfusion.com"

# ---------------------------------------------------------------------------
# Minimal inline FusionClient for discovery
# ---------------------------------------------------------------------------

class FusionDiscoveryError(Exception):
    """Raised when Fusion discovery fails."""
    pass


class FusionDiscoverer:
    """Logs into Apex Fusion and discovers controller config."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ReefMind/1.0",
        })
        self.csrf: Optional[str] = None

    def _get(self, path: str) -> Any:
        url = f"{FUSION_BASE}{path}"
        headers = {}
        if self.csrf:
            headers["csrf-token"] = self.csrf
        resp = self._session.get(url, headers=headers, timeout=30)
        if resp.status_code == 401:
            self.csrf = None
            raise FusionDiscoveryError("Session expired — re-login required")
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
            raise FusionDiscoveryError("Session expired — re-login required")
        resp.raise_for_status()
        return resp

    def login(self) -> dict:
        """Log in to Apex Fusion. Returns login response."""
        log.info("Fetching CSRF token from Fusion...")
        resp = self._get("/")
        html = resp.text

        import re
        m = re.search(r'csrf-token"\s+content="([^"]+)"', html)
        if not m:
            raise FusionDiscoveryError("Could not find CSRF token")
        self.csrf = m.group(1)
        log.debug("CSRF token obtained")

        log.info("Logging into Fusion as %s...", self.username)
        resp = self._post("/login", {
            "username": self.username,
            "password": self.password,
            "remember_me": True,
        })
        data = resp.json()

        if "redirect" not in data:
            raise FusionDiscoveryError(
                f"Login failed — unexpected response: {json.dumps(data)[:200]}"
            )

        log.info("Login succeeded — redirect: %s", data.get("redirect"))
        return data

    def discover(self) -> dict:
        """Full discovery: login → get account → get apex list → get config."""
        self.login()

        # Get account info to find controllers
        account = self._get("/api/account").json()
        log.info("Account: %s", account.get("username", "?"))

        # Discover Apex controllers
        apex_list = self._get("/api/apex").json()
        controllers = apex_list if isinstance(apex_list, list) else apex_list.get("apex", [])

        if not controllers:
            raise FusionDiscoveryError("No Apex controllers found on this account")

        results = []
        for ctrl in controllers:
            apex_id = ctrl.get("_id", ctrl.get("id", ""))
            name = ctrl.get("hostname", ctrl.get("name", ctrl.get("label", "Unnamed Apex")))
            log.info("Found controller: %s (%s)", name, apex_id)

            # Fetch full controller config — this gives us all probes/outputs in one call
            apex_detail = self._get(f"/api/apex/{apex_id}").json()

            # Extract probes from config inputs
            config_inputs = apex_detail.get("config", {}).get("inputs", [])
            # Extract live probe values from status inputs
            status_inputs_map = {}
            for inp in apex_detail.get("status", {}).get("inputs", []):
                status_inputs_map[inp.get("did", "")] = {
                    "value": inp.get("value"),
                    "unit": inp.get("unit", ""),
                }

            discovered_probes = []
            for inp in config_inputs:
                did = inp.get("did", "")
                pname = inp.get("name", did)
                ptype = inp.get("type", "Unknown")

                # Map known probe types
                SIMPLE_PROBE_TYPES = {"Temp", "pH", "ORP", "Salinity", "Cond", "Salt", "Amps", "Watts"}
                if ptype not in SIMPLE_PROBE_TYPES:
                    if did.startswith("Tmp"):
                        ptype = "Temp"
                    elif did.startswith("pH"):
                        ptype = "pH"
                    elif did.startswith("ORP"):
                        ptype = "ORP"
                    elif did.startswith("Sal"):
                        ptype = "Salinity"

                # Only include actual probe/sensor types, skip pwr/amp probes for non-vital
                probe_value = status_inputs_map.get(did, {}).get("value", None)

                discovered_probes.append({
                    "did": did,
                    "name": pname,
                    "type": ptype,
                    "unit": self._probe_unit(ptype),
                    "value": probe_value,
                })

            # Build outlet info from config outputs + status
            config_outputs = apex_detail.get("config", {}).get("outputs", [])
            status_outputs_map = {}
            for out in apex_detail.get("status", {}).get("outputs", []):
                status_outputs_map[out.get("did", "")] = out.get("status", [])

            discovered_outlets = []
            for out in config_outputs:
                outlet_state = status_outputs_map.get(out.get("did", ""), [])
                discovered_outlets.append({
                    "did": out.get("did", ""),
                    "name": out.get("name", ""),
                    "type": out.get("type", ""),
                    "state": outlet_state[0] if isinstance(outlet_state, list) and len(outlet_state) > 0 else "",
                })

            # Get system info
            hardware = apex_detail.get("hardware", "")
            software = apex_detail.get("software", "")
            serial = apex_detail.get("serial", "")

            results.append({
                "apex_id": apex_id,
                "name": name,
                "type": ctrl.get("type", ""),
                "serial": serial,
                "hardware": hardware,
                "software": software,
                "timezone": apex_detail.get("timezone", ""),
                "probes": discovered_probes,
                "outlets": discovered_outlets,
            })

        return {
            "controllers": results,
            "account": {
                "username": account.get("username", ""),
                "email": account.get("email", ""),
            }
        }

    def _probe_unit(self, ptype: str) -> str:
        """Map probe type to display unit."""
        mapping = {
            "Temp": "°F",
            "pH": "pH",
            "ORP": "mV",
            "Salinity": "PPT",
            "Cond": "µS",
            "Salt": "PPT",
            "Amps": "A",
            "Watts": "W",
        }
        return mapping.get(ptype, "raw")

    def close(self):
        self._session.close()


# ---------------------------------------------------------------------------
# Convenience function for the API layer
# ---------------------------------------------------------------------------

def discover_apex_fusion(username: str, password: str) -> dict:
    """Discover Apex controller(s) from Fusion credentials.

    Returns a dict with:
        controllers: list of discovered controllers with probes and outlets
        account: account metadata

    Raises FusionDiscoveryError on auth failure or connection issues.
    """
    discoverer = FusionDiscoverer(username, password)
    try:
        result = discoverer.discover()
        return result
    except requests.exceptions.RequestException as e:
        raise FusionDiscoveryError(f"Cannot reach Apex Fusion: {e}")
    finally:
        discoverer.close()
