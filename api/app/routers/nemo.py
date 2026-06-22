"""Nemo AI router — reef-keeping assistant with tank data awareness.

Optimizations:
- Tank data only fetched and injected for tank-specific questions
- Outlet states summarized instead of full list
- Tank data cached in-memory for 60s (Fusion data changes slowly)
- Base prompt stays lean
"""

import time
import json
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import TenantConfig
from app.middleware.auth import get_current_user
from app.config import get_settings
from app.services.fusion_live import FusionLiveClient, FusionLiveError

router = APIRouter(prefix="/api/nemo", tags=["nemo"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NemoQuestion(BaseModel):
    question: str

class NemoResponse(BaseModel):
    answer: str
    model: str = "deepseek"


# ---------------------------------------------------------------------------
# System prompt (base only — tank context appended dynamically)
# ---------------------------------------------------------------------------

NEMO_SYSTEM_PROMPT = """You are Nemo, a knowledgeable reef-keeping AI assistant. You help reef aquarium enthusiasts with:

- Water chemistry (temperature, salinity, pH, alkalinity, calcium, magnesium, etc.)
- Equipment selection and setup (protein skimmers, lights, pumps, reactors)
- Fish and coral health and disease
- Tank cycling and maintenance
- Aquarium troubleshooting
- General reefing best practices

When the user's tank data is available (provided below in TANK DATA), use it to give personalized, specific advice about their actual readings and equipment. When no tank data is provided, give general advice.

Answer clearly and concisely. If you don't know something, say so. Always prioritize the safety of the aquarium's inhabitants."""


# ---------------------------------------------------------------------------
# Tank data cache (in-memory, 60s TTL)
# ---------------------------------------------------------------------------

TANK_CACHE_TTL = 60
_tank_cache: dict[str, tuple[float, str]] = {}

def _cache_key(config: TenantConfig) -> str:
    return f"{config.tenant_id}:{config.fusion_apex_id}"


# ---------------------------------------------------------------------------
# Relevance: only fetch tank data for tank-specific questions
# ---------------------------------------------------------------------------

TANK_PATTERNS = re.compile(
    r"\b(?:my tank|my water|my ph|my temp(?:erature)?|my salinity|"
    r"my alk(?:alinity)?|my calcium|my magnesium|my nitrate|my phosphate|"
    r"my orp|my carx|my reactor|my skimmer|my heater|my pump|"
    r"tank doing|tank status|water quality|"
    r"how.+(?:tank|water|ph|temp|salinity|alk|calcium|reef)|"
    r"(?:check|review|look at).+(?:tank|water|param))\b",
    re.IGNORECASE,
)

# Probe/piece of equipment names from the tank — checked only if we have data
_tank_probe_names: set[str] = set()
_tank_outlet_names: set[str] = set()

def _question_needs_tank_data(question: str, config: TenantConfig) -> bool:
    """Quick keyword check — does this question reference the user's tank?"""
    if TANK_PATTERNS.search(question):
        return True

    # Check if any probe or outlet name appears in the question
    q_lower = question.lower()
    for name in _tank_probe_names:
        if name.lower() in q_lower:
            return True
    for name in _tank_outlet_names:
        if name.lower() in q_lower:
            return True

    return False


# ---------------------------------------------------------------------------
# Tank context builders
# ---------------------------------------------------------------------------

def _build_setup_context(config: TenantConfig) -> str:
    """Short controller description from stored config_json."""
    try:
        meta = json.loads(config.config_json) if config.config_json else {}
    except (json.JSONDecodeError, TypeError):
        return ""

    controllers = meta.get("controllers", [])
    if not controllers:
        return ""
    ctrl = controllers[0]

    probes = ctrl.get("probes", [])
    active = [p for p in probes if p.get("type") in ("Temp", "pH", "ORP", "Cond", "Salinity")]

    # Cache probe names for relevance matching
    global _tank_probe_names, _tank_outlet_names
    _tank_probe_names = {p.get("name", "") for p in active if p.get("name")}
    _tank_outlet_names = {o.get("name", "") for o in ctrl.get("outlets", []) if o.get("name")}

    lines = [f"Controller: {ctrl.get('name', '?')} ({ctrl.get('type', '?')})"]
    if active:
        lines.append(f"Probes: {', '.join(p['name'] for p in active)}")
    return "; ".join(lines)


def _build_live_context(config: TenantConfig) -> str:
    """Fetch live readings from Fusion, build concise context string.

    Cached for TANK_CACHE_TTL seconds.
    """
    global _tank_cache
    key = _cache_key(config)

    # Check cache
    now = time.time()
    if key in _tank_cache and now - _tank_cache[key][0] < TANK_CACHE_TTL:
        return _tank_cache[key][1]

    try:
        client = FusionLiveClient(config.fusion_user, config.fusion_pass)
        client.login()
        readings = client.get_live_readings(config.fusion_apex_id)
        outlets = client.get_all_outlet_states(config.fusion_apex_id)
        client.close()

        parts = []

        # Probe readings — always short (4-5 lines)
        if readings:
            parts.append("Readings: " + ", ".join(
                f"{r['probe_name']}={r['value']}{r.get('unit','')}"
                for r in readings
            ))
        else:
            parts.append("Readings: (none)")

        # Outlet summary instead of full list
        if outlets:
            on_outlets = [o for o in outlets if o.get("state") in ("ON", "AON", "PF1", "PF2", "PF3", "PF4")]
            off_outlets = [o for o in outlets if o.get("state") in ("OFF", "AOF")]
            summary = f"Outlets: {len(on_outlets)} ON, {len(off_outlets)} OFF"
            # List key equipment that's ON
            key_names = [o["name"] for o in on_outlets if o.get("type") in ("outlet", "variable")]
            if key_names:
                # Only show first 8 key outlets
                shown = key_names[:8]
                summary += f" — Active: {', '.join(shown)}"
                if len(key_names) > 8:
                    summary += f" +{len(key_names)-8} more"
            parts.append(summary)

        context = " | ".join(parts)

        # Cache it
        _tank_cache[key] = (now, context)
        return context

    except (FusionLiveError, Exception) as e:
        err_msg = f"(data unavailable: {e})"
        _tank_cache[key] = (now, err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def nemo_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        return {"configured": False}

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False}

    has_key = bool(config.nemo_api_key.strip() if config.nemo_api_key else False)
    env_key = get_settings().nemo_api_key

    return {
        "configured": has_key or bool(env_key),
        "provider": config.nemo_provider if has_key else "env",
        "model": config.nemo_model if has_key else "default",
        "source": "tenant" if has_key else ("env" if env_key else "none"),
    }


@router.post("/ask", response_model=NemoResponse)
async def ask_nemo(
    req: NemoQuestion,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # ---- Resolve API key ----
    api_key = ""
    provider = "deepseek"
    model = "deepseek-chat"
    api_base = "https://api.deepseek.com/v1"
    config = None

    tenant_id = user.get("tenant_id", "")
    if tenant_id:
        result = await db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        config = result.scalar_one_or_none()
        if config and config.nemo_api_key:
            api_key = config.nemo_api_key
            provider = config.nemo_provider or "deepseek"
            model = config.nemo_model or "deepseek-chat"

    if not api_key:
        api_key = settings.nemo_api_key
        if settings.nemo_provider:
            provider = settings.nemo_provider
        if settings.nemo_model:
            model = settings.nemo_model

    if not api_key:
        return NemoResponse(
            answer="Nemo AI is not configured yet. Go to Settings → AI Assistant to enter your API key.",
            model="offline",
        )

    # ---- Build system prompt (with or without tank data) ----
    tank_context_parts = []

    if config and config.fusion_apex_id:
        # Setup info (always included once — it's just a line or two)
        setup_info = _build_setup_context(config)
        if setup_info:
            tank_context_parts.append(setup_info)

        # Live data — only if question is about the tank
        if _question_needs_tank_data(req.question, config):
            live_data = _build_live_context(config)
            if live_data:
                tank_context_parts.append(live_data)

    if tank_context_parts:
        full_prompt = f"{NEMO_SYSTEM_PROMPT}\n\nTANK DATA\n{'─' * 40}\n" + "\n".join(tank_context_parts)
    else:
        full_prompt = NEMO_SYSTEM_PROMPT

    # ---- Call AI provider ----
    provider_bases = {
        "deepseek": "https://api.deepseek.com/v1",
        "openai": "https://api.openai.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
        "anthropic": "https://api.anthropic.com/v1",
    }
    if provider in provider_bases:
        api_base = provider_bases[provider]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": full_prompt},
                        {"role": "user", "content": req.question},
                    ],
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                answer = data["choices"][0]["message"]["content"]
            else:
                answer = f"Nemo API returned {resp.status_code}. Check your API key in Settings."

    except Exception as e:
        answer = f"Nemo couldn't reach the AI provider: {str(e)}"

    return NemoResponse(answer=answer, model=model)
