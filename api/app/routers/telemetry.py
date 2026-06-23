from fastapi import APIRouter, Depends, HTTPException, Query
from app.middleware.auth import get_current_user
from app.services.influx import query_telemetry, query_outlets, query_water_tests, query_notes, query_controller_info

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/summary")
async def get_summary(user: dict = Depends(get_current_user)):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get latest reading for each probe type
    results = query_telemetry(tenant_id, duration="1h")

    # Deduplicate to latest per probe
    latest = {}
    for r in results:
        name = r["probe_name"]
        if name not in latest or r["time"] > latest[name]["time"]:
            latest[name] = r

    return {"readings": list(latest.values())}


@router.get("/outlets")
async def get_outlets(user: dict = Depends(get_current_user)):
    """Get latest outlet states from InfluxDB (collected data)."""
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = query_outlets(tenant_id)
    return {"outlets": results, "source": "agent"}


@router.get("/{probe_name}")
async def get_probe_data(
    probe_name: str,
    duration: str = Query("24h", description="Time range (e.g. 24h, 7d, 30d)"),
    user: dict = Depends(get_current_user),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = query_telemetry(tenant_id, probe_name=probe_name, duration=duration)
    return {"probe": probe_name, "data": results}


@router.get("/water-tests")
async def get_water_tests(user: dict = Depends(get_current_user)):
    """Get all water test results for this tenant.
    
    Returns water test readings (KH, Ca, Mg, NO3, PO4) grouped by parameter.
    """
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = query_water_tests(tenant_id)
    return {"water_tests": results}


@router.get("/notes")
async def get_notes(user: dict = Depends(get_current_user)):
    """Get tank notes for this tenant.
    
    Returns tank notes (observations, maintenance, events) ordered by most recent.
    """
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = query_notes(tenant_id)
    return {"notes": results}


@router.get("/controller")
async def get_controller_info(user: dict = Depends(get_current_user)):
    """Get controller hardware/software/serial info."""
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    info = query_controller_info(tenant_id)
    return {"controller": info}


