"""Fusion API router — discovery, configuration, and live data."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import TenantConfig
from app.middleware.auth import get_current_user
from app.services.fusion_discovery import discover_apex_fusion, FusionDiscoveryError
from app.services.fusion_live import (
    fetch_live_readings,
    fetch_probe_history,
    fetch_outlet_states,
    FusionLiveError,
    load_tenant_config,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/api/fusion", tags=["fusion"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FusionDiscoverRequest(BaseModel):
    fusion_username: str
    fusion_password: str


class FusionSaveRequest(BaseModel):
    controller_id: str
    discovered_data: dict


class FusionSaveResponse(BaseModel):
    status: str
    message: str


# ---------------------------------------------------------------------------
# Discovery & Config
# ---------------------------------------------------------------------------

@router.post("/discover")
async def fusion_discover(
    req: FusionDiscoverRequest,
):
    """Log into Apex Fusion and discover controller(s), probes, and metadata."""
    if not req.fusion_username or not req.fusion_password:
        raise HTTPException(status_code=400, detail="Fusion username and password are required")

    try:
        result = discover_apex_fusion(req.fusion_username, req.fusion_password)
        return {
            "status": "ok",
            "discovered": result,
        }
    except FusionDiscoveryError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fusion API error: {str(e)}")


@router.post("/save", response_model=FusionSaveResponse)
async def fusion_save(
    req: FusionSaveRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Save discovered Fusion configuration to the user's tenant config."""
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    import uuid
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Tenant config not found")

    # Update config
    config.fusion_apex_id = req.controller_id

    # Store full discovered data as JSON
    import json
    full_meta = {
        "controller_id": req.controller_id,
        "controllers": req.discovered_data.get("controllers", []),
        "account": req.discovered_data.get("account", {}),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }
    config.config_json = json.dumps(full_meta)

    await db.commit()

    # Trigger immediate mlog and notes collection for this tenant
    try:
        from app.services.collector import _collect_mlog, _collect_notes
        tcfg = {
            "tenant_id": tenant_id,
            "fusion_user": config.fusion_user,
            "fusion_pass": config.fusion_pass,
            "fusion_apex_id": req.controller_id,
        }
        mlog_result = _collect_mlog(tcfg)
        notes_result = _collect_notes(tcfg)
        print(f"Immediate sync: mlog={mlog_result['records']} records, notes={notes_result['records']} records")
    except Exception as e:
        print(f"Immediate sync error (non-fatal): {e}")

    return FusionSaveResponse(
        status="ok",
        message=f"Configuration saved for controller {req.controller_id}",
    )


@router.get("/status")
async def fusion_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check Fusion connection status for the current user's tenant."""
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    import uuid
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tid)
    )
    config = result.scalar_one_or_none()

    if not config:
        return {"connected": False, "detail": "No configuration found"}

    has_creds = bool(config.fusion_user.strip() if config.fusion_user else False)
    has_apex_id = bool(config.fusion_apex_id.strip() if config.fusion_apex_id else False)

    return {
        "connected": has_creds and has_apex_id,
        "fusion_user": config.fusion_user or "",
        "fusion_apex_id": config.fusion_apex_id or "",
        "has_creds": has_creds,
        "has_apex_id": has_apex_id,
        "discovered": bool(config.config_json and config.config_json != "{}"),
    }


# ---------------------------------------------------------------------------
# Live Data (no agent required)
# ---------------------------------------------------------------------------

@router.get("/readings")
async def fusion_readings(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get live probe readings directly from Apex Fusion.

    Falls back to Fusion's live API when no local agent is deployed.
    Returns same format as telemetry/summary: {readings: [...]}.
    """
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        config = await load_tenant_config(tenant_id, db)
        readings = fetch_live_readings(config)
        return {"readings": readings, "source": "fusion"}
    except FusionLiveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fusion live data error: {str(e)}")


@router.get("/history/{probe_did}")
async def fusion_probe_history(
    probe_did: str,
    hours: int = Query(6, description="Hours of history to fetch"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get probe history from Fusion ilog for charting.

    Args:
        probe_did: The probe's 'did' field (e.g. 'base_Temp', 'base_pH')
        hours: How many hours of history (max 24)
    """
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        config = await load_tenant_config(tenant_id, db)
        hours = min(hours, 24)  # Fusion's ilog caps at ~7 days, keep it sensible
        history = fetch_probe_history(config, probe_did, hours=hours)
        return {"probe": probe_did, "data": history, "source": "fusion"}
    except FusionLiveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fusion history error: {str(e)}")


@router.get("/outlets")
async def fusion_outlets(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current outlet states directly from Apex Fusion."""
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        config = await load_tenant_config(tenant_id, db)
        outlets = fetch_outlet_states(config)
        return {"outlets": outlets, "source": "fusion"}
    except FusionLiveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fusion outlet error: {str(e)}")
