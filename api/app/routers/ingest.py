from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.auth import get_current_user
from app.services.influx import write_telemetry, write_outlets, write_power
from app.schemas.ingest import TelemetryBatch, OutletBatch, PowerBatch

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/telemetry")
async def ingest_telemetry(
    batch: TelemetryBatch,
    request: Request,
    user: dict = Depends(get_current_user),
):
    if user.get("auth_type") != "api_key":
        raise HTTPException(status_code=403, detail="Agent API key required")

    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid API key")

    readings = [r.model_dump() for r in batch.readings]
    count = write_telemetry(tenant_id, readings)
    return {"status": "ok", "writes": count}


@router.post("/outlets")
async def ingest_outlets(
    batch: OutletBatch,
    request: Request,
    user: dict = Depends(get_current_user),
):
    if user.get("auth_type") != "api_key":
        raise HTTPException(status_code=403, detail="Agent API key required")

    tenant_id = user.get("tenant_id", "")
    outlets = [o.model_dump() for o in batch.outlets]
    count = write_outlets(tenant_id, outlets)
    return {"status": "ok", "writes": count}


@router.post("/power")
async def ingest_power(
    batch: PowerBatch,
    request: Request,
    user: dict = Depends(get_current_user),
):
    if user.get("auth_type") != "api_key":
        raise HTTPException(status_code=403, detail="Agent API key required")

    tenant_id = user.get("tenant_id", "")
    readings = [r.model_dump() for r in batch.readings]
    count = write_power(tenant_id, readings)
    return {"status": "ok", "writes": count}
