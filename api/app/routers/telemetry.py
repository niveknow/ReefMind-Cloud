from fastapi import APIRouter, Depends, HTTPException, Query
from app.middleware.auth import get_current_user
from app.services.influx import query_telemetry, query_outlets

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


