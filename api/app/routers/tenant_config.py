from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import TenantConfig
from app.middleware.auth import get_current_user
from app.services.auth import create_api_key

router = APIRouter(prefix="/api/tenant", tags=["tenant"])


@router.get("/config")
async def get_config(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"config": {}}

    # Return config without exposing secrets (no api keys)
    return {
        "config": {
            "backend_type": config.backend_type,
            "config_json": config.config_json,
            "fusion_config_configured": bool(config.fusion_user and config.fusion_pass),
            "agent_api_key": config.agent_api_key,
            "nemo_configured": config.nemo_configured,
            "nemo_provider": config.nemo_provider,
            "nemo_model": config.nemo_model,
        }
    }


@router.put("/config")
async def update_config(
    data: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    if "config_json" in data:
        config.config_json = data["config_json"]
    if "fusion_user" in data:
        config.fusion_user = data["fusion_user"]
    if "fusion_pass" in data:
        config.fusion_pass = data["fusion_pass"]
    if "fusion_apex_id" in data:
        config.fusion_apex_id = data["fusion_apex_id"]
    if "nemo_api_key" in data:
        config.nemo_api_key = data["nemo_api_key"]
        config.nemo_configured = bool(data["nemo_api_key"])
    if "nemo_provider" in data:
        config.nemo_provider = data["nemo_provider"]
    if "nemo_model" in data:
        config.nemo_model = data["nemo_model"]
    if "backfill_days" in data:
        import json
        try:
            existing = json.loads(config.config_json) if isinstance(config.config_json, str) else config.config_json or {}
        except (json.JSONDecodeError, TypeError):
            existing = {}
        existing["backfill_days"] = int(data["backfill_days"])
        existing["backfill_complete"] = False  # reset to trigger re-backfill
        config.config_json = json.dumps(existing)

    await db.commit()
    return {"status": "ok"}


@router.post("/regenerate-agent-key")
async def regenerate_agent_key(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    config.agent_api_key = create_api_key()
    await db.commit()

    return {"agent_api_key": config.agent_api_key}
