"""Fusion data collector — periodically polls Fusion API and stores
readings in InfluxDB, just like the local Apex collector did.

Runs in the background via the FastAPI lifespan. Polls every 5 minutes
for all tenants with Fusion configured.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from app.database import engine
from app.config import get_settings
from app.services.influx import write_telemetry, write_outlets, write_water_tests, write_notes
from app.services.fusion_live import FusionLiveClient, FusionLiveError

log = logging.getLogger("reefmind.collector")

POLL_INTERVAL_SECONDS = 300  # 5 minutes
MLOG_POLL_INTERVAL_SECONDS = 21600  # 6 hours
NOTES_POLL_INTERVAL_SECONDS = 21600  # 6 hours
BACKFILL_DAYS = 7  # Days of ilog history to write on first run

# Track last poll per tenant for dedup
_last_poll: dict[str, datetime] = {}
_last_mlog_poll: dict[str, datetime] = {}
_last_notes_poll: dict[str, datetime] = {}


# ---------------------------------------------------------------------------
# Per-tenant collection
# ---------------------------------------------------------------------------

def _collect_tenant(tcfg: dict) -> dict:
    """Collect one tenant's Fusion data and write to InfluxDB.

    tcfg: dict with keys: tenant_id, fusion_user, fusion_pass, fusion_apex_id
    Returns a dict with counts of what was written.
    """
    tenant_id = tcfg["tenant_id"]
    result = {"readings": 0, "outlets": 0, "status": "ok"}

    if not tcfg.get("fusion_user") or not tcfg.get("fusion_pass") or not tcfg.get("fusion_apex_id"):
        result["status"] = "skipped (no fusion config)"
        return result

    try:
        client = FusionLiveClient(tcfg["fusion_user"], tcfg["fusion_pass"])
        client.login()
        apex_id = tcfg["fusion_apex_id"]

        # --- 1. Live readings from /api/apex/{id} status inputs ---
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
            count = write_telemetry(tenant_id, readings)
            result["readings"] = count
            log.info("Tenant %s: wrote %d live readings", tenant_id[:8], count)

        # --- 2. Outlet states ---
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
                "state": is_on,
                "state_display": state_str,
                "timestamp": now,
            })

        if outlet_points:
            count = write_outlets(tenant_id, outlet_points)
            result["outlets"] = count

        client.close()

    except (FusionLiveError, Exception) as e:
        result["status"] = f"error: {e}"
        log.error("Tenant %s collection failed: %s", tenant_id[:8], e)
        client.close()

    return result


def _collect_mlog(tcfg: dict) -> dict:
    """Fetch water test results (mlog) from Fusion for one tenant.
    
    tcfg: dict with keys: tenant_id, fusion_user, fusion_pass, fusion_apex_id
    Returns a dict with counts of what was written.
    """
    tenant_id = tcfg["tenant_id"]
    result = {"records": 0, "status": "ok"}

    if not tcfg.get("fusion_user") or not tcfg.get("fusion_pass") or not tcfg.get("fusion_apex_id"):
        result["status"] = "skipped (no fusion config)"
        return result

    try:
        client = FusionLiveClient(tcfg["fusion_user"], tcfg["fusion_pass"])
        client.login()
        apex_id = tcfg["fusion_apex_id"]

        data = client.get_mlog(apex_id, days=365)
        if data:
            count = write_water_tests(tenant_id, data)
            result["records"] = count
            log.info("Tenant %s: wrote %d water test records", tenant_id[:8], count)
        else:
            log.info("Tenant %s: no mlog data returned", tenant_id[:8])

        client.close()
    except (FusionLiveError, Exception) as e:
        result["status"] = f"error: {e}"
        log.error("Tenant %s mlog collection failed: %s", tenant_id[:8], e)

    return result


def _collect_notes(tcfg: dict) -> dict:
    """Fetch tank notes from Fusion for one tenant.
    
    tcfg: dict with keys: tenant_id, fusion_user, fusion_pass, fusion_apex_id
    Returns a dict with counts of what was written.
    """
    tenant_id = tcfg["tenant_id"]
    result = {"records": 0, "status": "ok"}

    if not tcfg.get("fusion_user") or not tcfg.get("fusion_pass") or not tcfg.get("fusion_apex_id"):
        result["status"] = "skipped (no fusion config)"
        return result

    try:
        client = FusionLiveClient(tcfg["fusion_user"], tcfg["fusion_pass"])
        client.login()
        apex_id = tcfg["fusion_apex_id"]

        notes_result = client.get_notes(apex_id, page=1, per_page=200)
        notes_list = notes_result[1] if isinstance(notes_result, list) and len(notes_result) > 1 else []

        if notes_list:
            count = write_notes(tenant_id, notes_list)
            result["records"] = count
            log.info("Tenant %s: wrote %d tank notes", tenant_id[:8], count)
        else:
            log.info("Tenant %s: no notes data returned", tenant_id[:8])

        client.close()
    except (FusionLiveError, Exception) as e:
        result["status"] = f"error: {e}"
        log.error("Tenant %s notes collection failed: %s", tenant_id[:8], e)

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
                       tc.fusion_apex_id
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

                    # ── Mlog (water tests) — every 6 hours ──────────────
                    now = datetime.now(timezone.utc)
                    last_mlog = _last_mlog_poll.get(tcfg["tenant_id"])
                    if not last_mlog or (now - last_mlog).total_seconds() >= MLOG_POLL_INTERVAL_SECONDS:
                        mlog_result = _collect_mlog(tcfg)
                        if mlog_result["status"] == "ok":
                            _last_mlog_poll[tcfg["tenant_id"]] = now
                            log.info("Tenant %s: water tests collection done (%d records)",
                                     tid, mlog_result["records"])
                        elif "error" in mlog_result["status"]:
                            log.warning("Tenant %s: water tests failed: %s",
                                        tid, mlog_result["status"])

                    # ── Notes — every 6 hours ───────────────────────────
                    last_notes = _last_notes_poll.get(tcfg["tenant_id"])
                    if not last_notes or (now - last_notes).total_seconds() >= NOTES_POLL_INTERVAL_SECONDS:
                        notes_result = _collect_notes(tcfg)
                        if notes_result["status"] == "ok":
                            _last_notes_poll[tcfg["tenant_id"]] = now
                            log.info("Tenant %s: notes collection done (%d records)",
                                     tid, notes_result["records"])
                        elif "error" in notes_result["status"]:
                            log.warning("Tenant %s: notes failed: %s",
                                        tid, notes_result["status"])

                log.info("Collection cycle complete — next poll in %ds", POLL_INTERVAL_SECONDS)

        except Exception as e:
            log.error("Collector loop error: %s", e)
            import traceback
            traceback.print_exc()

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
