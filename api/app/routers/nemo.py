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
from app.services.influx import query_water_tests, query_notes, query_telemetry

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

TANK DATA is provided below with live readings, water test history (365 days), tank notes (2 years), and probe history trends (24h, 7d, 30d, 90d ranges). Use this data to give personalized, specific advice. You CAN reference historical values — for example, you can compare current water tests against previous test dates, identify trends from the probe ranges, and reference past notes/events.

If the user asks about a specific date range not fully covered by the provided trends, explain what data you do have and give the best analysis possible from the ranges shown.

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
    """Fetch live readings from Fusion and historical data from InfluxDB.

    Cached for TANK_CACHE_TTL seconds.
    """
    global _tank_cache
    key = _cache_key(config)

    # Check cache
    now = time.time()
    if key in _tank_cache and now - _tank_cache[key][0] < TANK_CACHE_TTL:
        return _tank_cache[key][1]

    parts = []

    try:
        client = FusionLiveClient(config.fusion_user, config.fusion_pass)
        client.login()
        readings = client.get_live_readings(config.fusion_apex_id)
        outlets = client.get_all_outlet_states(config.fusion_apex_id)
        client.close()

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

    except (FusionLiveError, Exception) as e:
        parts.append(f"(live data unavailable: {e})")

    # ---- InfluxDB historical data (compact, always included) ----
    tenant_id = str(config.tenant_id)

    # Water tests — all records grouped by date (not just latest)
    try:
        wt = query_water_tests(tenant_id, duration="365d")
        if wt:
            # Group water tests by date
            from collections import defaultdict
            by_date: dict[str, dict[str, float]] = defaultdict(dict)
            date_order: list[str] = []
            for r in wt:
                d = r["time"][:10]  # YYYY-MM-DD
                if d not in by_date:
                    date_order.append(d)
                by_date[d][r["parameter"]] = r["value"]
            # Show last 12 test dates (most recent first)
            wt_lines = []
            for d in reversed(date_order[-12:]):
                params = by_date[d]
                vals = ", ".join(f"{p}={v}" for p, v in sorted(params.items()))
                wt_lines.append(f"{d}: {vals}")
            parts.append(f"Water test history ({len(wt)} records, last {len(wt_lines)} dates):\n  " + "\n  ".join(wt_lines))
    except Exception:
        pass  # non-fatal

    # Notes — last 50 with dates and details
    try:
        notes = query_notes(tenant_id, duration="730d", limit=50)
        if notes:
            note_lines = []
            for n in notes:
                d = n.get("time", "")[:10]
                tname = n.get("type_name", "")
                emoji = {"Event": "📌", "Maintenance": "🔧", "Good": "✅",
                         "Bad": "⚠️", "Ugly": "🚨"}.get(tname, "📝")
                title = n.get("title", "(untitled)")
                comment = n.get("comment", "")
                if comment:
                    note_lines.append(f"{d} {emoji} {title}: {comment}")
                else:
                    note_lines.append(f"{d} {emoji} {title}")
            parts.append("Recent notes:\n  " + "\n  ".join(note_lines))
    except Exception:
        pass

    # Probe history — 24h, 7d, 30d min/max/avg per probe
    for duration_label, duration_val in [("24h", "24h"), ("7d", "7d"), ("30d", "30d"), ("90d", "90d")]:
        try:
            all_data = query_telemetry(tenant_id, duration=duration_val)
            if all_data:
                from collections import defaultdict
                probe_stats: dict[str, dict] = defaultdict(lambda: {"values": [], "unit": ""})
                for r in all_data:
                    name = r.get("probe_name", "")
                    if name:
                        probe_stats[name]["values"].append(r.get("value", 0))
                        probe_stats[name]["unit"] = r.get("unit", "")

                stat_lines = []
                for name, data in sorted(probe_stats.items()):
                    vals = data["values"]
                    unit = data["unit"]
                    if vals:
                        mn, mx, avg = min(vals), max(vals), round(sum(vals) / len(vals), 2)
                        stat_lines.append(f"{name} {mn}-{mx} ({avg} avg){unit}")
                if stat_lines:
                    parts.append(f"Probe trend ({duration_label}): " + "; ".join(stat_lines))
        except Exception:
            pass

    context = " | ".join(parts)

    # Cache it
    _tank_cache[key] = (now, context)
    return context


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

        # Tank data — always included (live + InfluxDB water tests, notes, trends)
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
