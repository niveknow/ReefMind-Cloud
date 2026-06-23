"""Fusion data collector — periodically polls Fusion API and stores
readings in InfluxDB, just like the local Apex collector did.

Runs in the background via the FastAPI lifespan. Polls every 5 minutes
for all tenants with Fusion configured.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from app.database import engine
from app.config import get_settings
from app.services.influx import write_telemetry, write_outlets, write_water_tests, write_notes, write_power
from app.services.fusion_live import FusionLiveClient, FusionLiveError

log = logging.getLogger("reefmind.collector")

POLL_INTERVAL_SECONDS = 300  # 5 minutes
BACKFILL_DAYS = 7  # Days of ilog history to write on first run

# All available data areas for user selection
ALL_AREAS = ["probes", "outlets", "water_tests", "notes", "power", "trident"]

# Track last poll per tenant for dedup
_last_poll: dict[str, datetime] = {}


# ---------------------------------------------------------------------------
# Per-tenant collection
# ---------------------------------------------------------------------------

def _collect_tenant(tcfg: dict) -> dict:
    """Collect one tenant's Fusion data and write to InfluxDB.

    tcfg: dict with keys: tenant_id, fusion_user, fusion_pass, fusion_apex_id, config_json
    enabled_areas is read from config_json; defaults to ALL_AREAS.
    Returns a dict with counts of what was written.
    """
    tenant_id = tcfg["tenant_id"]
    result = {"readings": 0, "outlets": 0, "water_tests": 0, "notes": 0, "power": 0, "status": "ok"}

    if not tcfg.get("fusion_user") or not tcfg.get("fusion_pass") or not tcfg.get("fusion_apex_id"):
        result["status"] = "skipped (no fusion config)"
        return result

    # Parse enabled areas from config_json; default to all if not set
    enabled: set[str] = set(ALL_AREAS)
    config_json_raw = tcfg.get("config_json", "")
    if config_json_raw and config_json_raw != "{}":
        try:
            meta = json.loads(config_json_raw) if isinstance(config_json_raw, str) else config_json_raw
            if "enabled_areas" in meta and isinstance(meta["enabled_areas"], list) and len(meta["enabled_areas"]) > 0:
                enabled = set(meta["enabled_areas"])
        except (json.JSONDecodeError, TypeError):
            pass  # fall through to all enabled

    log.info("Tenant %s: enabled areas: %s", tenant_id[:8], sorted(enabled))

    try:
        client = FusionLiveClient(tcfg["fusion_user"], tcfg["fusion_pass"])
        client.login()
        apex_id = tcfg["fusion_apex_id"]

        # Determine which areas need the apex detail call
        needs_detail = bool({"probes", "outlets", "power"} & enabled)

        # Initialize shared variables (may be populated below)
        detail = None
        status_inputs = []
        config_inputs = []
        config_map = {}
        now = datetime.now(timezone.utc).isoformat()
        DISPLAY_NAMES = {}
        PROBE_UNITS = {}

        if needs_detail:
            detail = client._get(f"/api/apex/{apex_id}").json()
            status_inputs = detail.get("status", {}).get("inputs", [])
            config_inputs = detail.get("config", {}).get("inputs", [])
            now = datetime.now(timezone.utc).isoformat()

            # Build probe name/type map from config
            config_map = {}
            for inp in config_inputs:
                did = inp.get("did", "")
                config_map[did] = {
                    "name": inp.get("name", did),
                    "type": inp.get("type", "Unknown"),
                }

            # Map probe DIDs to display names (same logic as fusion_live)
            DISPLAY_NAMES = {
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

        # --- 1. Live probe readings ---
        if "probes" in enabled:
            readings = []
            for inp in status_inputs:
                did = inp.get("did", "")
                value = inp.get("value")
                if value is None:
                    continue

                cfg = config_map.get(did, {})
                ptype = cfg.get("type", "Unknown")

                # Only store sensor-type readings
                sensor_types = {"Temp", "pH", "ORP", "Cond", "Salinity"}
                if did.startswith("Tmp"):
                    ptype = "Temp"
                elif did.startswith("pH"):
                    ptype = "pH"
                elif did.startswith("ORP"):
                    ptype = "ORP"
                elif did.startswith("Sal"):
                    ptype = "Salinity"
                elif did.startswith("base_Cond"):
                    ptype = "Cond"

                if ptype not in sensor_types:
                    continue

                try:
                    val = float(value)
                except (ValueError, TypeError):
                    continue

                readings.append({
                    "did": did,
                    "probe_name": DISPLAY_NAMES.get(did, cfg.get("name", did)),
                    "probe_type": ptype,
                    "unit": PROBE_UNITS.get(ptype, "raw"),
                    "value": val,
                    "timestamp": now,
                })

            if readings:
                count = write_telemetry(tenant_id, readings, apex_id=apex_id)
                result["readings"] = count
                log.info("Tenant %s: wrote %d live readings", tenant_id[:8], count)

        # --- 2. Outlet states ---
        if "outlets" in enabled:
            config_outputs = detail.get("config", {}).get("outputs", [])
            status_outputs = detail.get("status", {}).get("outputs", [])
            status_outputs_map = {}
            for o in status_outputs:
                status_outputs_map[o.get("did", "")] = o.get("status", [])

            outlet_points = []
            for out in config_outputs:
                state_arr = status_outputs_map.get(out.get("did", ""), [])
                state_str = state_arr[0] if isinstance(state_arr, list) and len(state_arr) > 0 else "OFF"
                is_on = int(state_str in ("ON", "AON", "PF1", "PF2", "PF3", "PF4"))
                outlet_points.append({
                    "outlet_name": out.get("name", ""),
                    "outlet_type": out.get("type", ""),
                    "state": is_on,
                    "state_display": state_str,
                    "timestamp": now,
                })

            if outlet_points:
                count = write_outlets(tenant_id, outlet_points, apex_id=apex_id)
                result["outlets"] = count

        # --- 3. Power/Energy probes (Watts, Amps) ---
        if "power" in enabled:
            power_points = []
            for inp in status_inputs:
                did = inp.get("did", "")
                value = inp.get("value")
                if value is None:
                    continue

                cfg = config_map.get(did, {})
                ptype = cfg.get("type", "Unknown")

                # Detect power-type probes
                if ptype not in ("Watts", "Amps"):
                    if "_Watts" in did or did.endswith("_w"):
                        ptype = "Watts"
                    elif "_Amps" in did or did.endswith("_a"):
                        ptype = "Amps"
                    else:
                        continue

                try:
                    val = float(value)
                except (ValueError, TypeError):
                    continue

                # Extract outlet name from DID (e.g., "OUT_1_Watts" -> "OUT_1")
                outlet_name = did
                for suffix in ("_Watts", "_Amps", "_w", "_a"):
                    if suffix in did:
                        outlet_name = did.split(suffix)[0]
                        break

                power_points.append({
                    "outlet_name": outlet_name,
                    "channel": ptype.lower(),
                    "watts": val if ptype == "Watts" else 0.0,
                    "amps": val if ptype == "Amps" else 0.0,
                    "timestamp": now,
                })

            if power_points:
                count = write_power(tenant_id, power_points, apex_id=apex_id)
                result["power"] = count
                log.info("Tenant %s: wrote %d power readings", tenant_id[:8], count)

        # --- 4. Water test logs (mlog) ---
        if "water_tests" in enabled:
            log.info("Tenant %s: fetching mlog water tests...", tenant_id[:8])
            try:
                mlog_data = client.get_mlog(apex_id, days=365)
                if mlog_data:
                    count = write_water_tests(tenant_id, mlog_data, apex_id=apex_id)
                    result["water_tests"] = count
                    log.info("Tenant %s: wrote %d water test records", tenant_id[:8], count)
                else:
                    log.info("Tenant %s: no mlog data returned", tenant_id[:8])
            except Exception as e:
                log.warning("Tenant %s: mlog fetch failed: %s", tenant_id[:8], e)

        # --- 5. Notes (logs) ---
        if "notes" in enabled:
            log.info("Tenant %s: fetching notes...", tenant_id[:8])
            try:
                notes_data = client.get_all_notes(apex_id, days=30)
                if notes_data:
                    count = write_notes(tenant_id, notes_data, apex_id=apex_id)
                    result["notes"] = count
                    log.info("Tenant %s: wrote %d notes", tenant_id[:8], count)
                else:
                    log.info("Tenant %s: no notes returned", tenant_id[:8])
            except Exception as e:
                log.warning("Tenant %s: notes fetch failed: %s", tenant_id[:8], e)

        client.close()

    except (FusionLiveError, Exception) as e:
        result["status"] = f"error: {e}"
        log.error("Tenant %s collection failed: %s", tenant_id[:8], e)

    return result


# ---------------------------------------------------------------------------
# Background collector loop
# ---------------------------------------------------------------------------

async def _get_configured_tenants():
    """Get all tenant configs with Fusion credentials."""
    from app.database import engine
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT tc.tenant_id::text, tc.fusion_user, tc.fusion_pass,
                       tc.fusion_apex_id, tc.config_json
                FROM tenant_configs tc
                WHERE tc.fusion_user != '' AND tc.fusion_pass != ''
                  AND tc.fusion_apex_id != ''
            """)
        )
        rows = result.fetchall()
        return [
            {
                "tenant_id": str(row[0]),
                "fusion_user": row[1],
                "fusion_pass": row[2],
                "fusion_apex_id": row[3],
                "config_json": row[4] or "{}",
            }
            for row in rows
        ]


async def collector_loop():
    """Background loop that polls Fusion and writes to InfluxDB."""
    log.info("Fusion collector started (polling every %ds)", POLL_INTERVAL_SECONDS)

    while True:
        try:
            tenants = await _get_configured_tenants()
            if not tenants:
                log.debug("No tenants with Fusion configured, skipping poll")
            else:
                log.info("Polling Fusion for %d tenant(s)", len(tenants))

                for tcfg in tenants:
                    result = _collect_tenant(tcfg)
                    tid = str(tcfg["tenant_id"])[:8]
                    if result["status"] == "ok":
                        log.info(
                            "Tenant %s: %d readings, %d outlets",
                            tid, result["readings"], result["outlets"],
                        )
                    elif "skipped" in result["status"]:
                        pass  # Normal for unconfigured tenants
                    else:
                        log.warning("Tenant %s: %s", tid, result["status"])

                log.info("Collection cycle complete -- next poll in %ds", POLL_INTERVAL_SECONDS)

        except Exception as e:
            log.error("Collector loop error: %s", e)
            import traceback
            traceback.print_exc()

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
