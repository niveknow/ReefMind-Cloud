# Changelog

## v0.1.4 — Notes History & Nemo Insights (2026-06-24)

**Extends tank notes to 24 months with month/week filtering and gives Nemo AI full access to note details for personalized insights.**

### 🐛 Bug Fixes

- **Empty note titles in backfill** — Notes with empty titles (e.g. Maintenance/Changed Media) caused InfluxDB HTTP 400 on the HTTP API backfill write. Fixed by resolving empty titles via `REASON_TITLES` mapping, same as the regular `write_notes()` function
- **Notes API capped at 100 results** — `query_notes()` had a default limit of 100, silently dropping ~half the notes in the 730d range. Changed to unlimited (0 = return all)
- **Stale InfluxDB client in notes backfill** — Backfill now uses direct InfluxDB HTTP API (`httpx.post` to `/api/v2/write`) instead of the Python client, which had a stale connection pool issue that silently dropped writes

### 🚀 Enhancements

- **Tank Notes page** — Added filter bar with time presets (All Time, 1 Year, 6 Months, 3 Months, This Month, This Week), a month-jump dropdown to jump to any month with notes, and month-grouped display with note counts per month
- **Notes history extended** — API `query_notes()` default duration increased from 365d to **730d** (24 months) so users with older Fusion notes can see their full history
- **Ask Nemo** — Nemo AI now receives **2 years / 50 notes** with full comment text (previously: 90 days / 10 notes with title only). Nemo can now answer questions like "what corals did I buy this year" or "show me all maintenance in January"
  - System prompt updated: `(90 days)` → `(2 years)`

### 📦 Data & Collector

- Notes backfill now covers **18 months** (540 days, monthly-chunked) via Fusion API
- 205 notes per tenant deduplicated from 206 raw across 12 monthly windows
- `notes_backfill_complete` flag stored in tenant `config_json` (PostgreSQL jsonb)

### 📚 Documentation

- `README.md` updated to reflect v0.1.4 features and accurate project structure
- `CHANGELOG.md` — this entry
- `docs/ANALYSIS-BACKLOG.md` — delivery statuses reconciled with GitHub issues

---

## v0.1.3 — Full Notes Backfill & Dashboard Fixes (2026-06-24)

**Implements comprehensive tank notes backfill with monthly-chunked fetching, historical probe data backfill extension, and dashboard stability fixes.**

### 🐛 Bug Fixes

- **Route ordering in telemetry.py** — Moved `/notes`, `/water-tests`, `/controller` routes before the wildcard `/{probe_name}` route so they resolve correctly
- **Dashboard duration buttons** — Added `duration` to React `useEffect` dependency arrays so 1h/6h/24h chart buttons actually reload data on click
- **Notes deduplication** — `_resolve_note_id()` handles Fusion API's MongoDB-style `_id` field, plus `REASON_TITLES` mapping for empty titles

### 🚀 Enhancements

- **Full notes backfill** — Collector iterates through 18 monthly windows (30–540 days back) via Fusion API, deduplicates by `note_id`, and writes via HTTP API to InfluxDB
- **Historical probe backfill** — 90-day chunked backfill (7-day windows) from Fusion `/logs` endpoint, with `min(backfill_days, 7)` cap and completion flag
- **Nemo AI context** — Injects full water test history, probe trends (24h/7d/30d/90d), and recent notes into system prompt for personalized advice
- **InfluxDB tag sorting** — Added `group()` and `aggregateWindow` to `query_telemetry` for stable tag-key ordering in chart queries

### 📦 Data & Collector

- Probe backfill: 5,840+ historical points per tenant
- Notes backfill: 205 notes per tenant captured
- Controller info (serial, HW, SW) collected every poll cycle

---

## v0.1.2 — Bug Fix Release (2026-06-23)

**Bug fix and stability release for the ReefMind Cloud SaaS platform.**

### 🐛 Bug Fixes

- **Route ordering** — Moved specific routes (`/notes`, `/water-tests`, `/controller`) before the wildcard `/{probe_name}` route so they resolve correctly instead of returning empty probe data
- **Controller info extraction** — Fixed `get_controller_info()` to extract serial/hardware/software from the Fusion API response top-level keys, not from a non-existent nested `"controller"` key
- **Collector logging** — Added dedicated StreamHandler to the collector logger so INFO-level poll cycle messages are visible (previously swallowed by root WARNING level)
- **Outlet query window** — Expanded `query_outlets()` time range from 30m to 6h to find data across container restarts
- **Duration button reload** — Added `duration` to React `useEffect` dependency arrays in `DashboardPage.tsx` so 1h/6h/24h chart buttons actually reload data when clicked
- **Outlet data for 020fe3d2 tenant** — Enabled `outlets` in data areas via SQL update so the collector writes outlet states

### 📦 Data & Collector

- **Historical probe backfill** — Reset backfill flag and triggered 7-day ilog backfill, importing 5,684 historical probe data points
- **Stale data cleanup** — Removed probe telemetry from old container run to prevent chart gaps when viewing 24h range
- **Collector now at INFO level** — All poll cycles, tenant activity, and data counts visible in container logs

### 📚 Documentation

- Added **Fusion API historical data limits** to the data-collection tables in ANALYSIS-BACKLOG.md

---

## v0.1.1 — Water Tests & Power Monitoring (2026-06-23)

**Adds water test (mlog) collection and per-outlet power monitoring.**

### 🚀 Enhancements

- **Water test collection** — `get_mlog()` method in FusionLiveClient, `write_water_tests()` in InfluxDB with atomic replace, collector pulls mlog data every 5 minutes
- **Water Test Page** — Frontend chart showing KH, Ca, Mg, NO3, PO4 history with inline trend charts
- **Power monitoring** — Collector detects Watts/Amps probes by DID suffix, `write_power()` writes to `apex_power` measurement
- **API endpoint** `GET /api/telemetry/water-tests`

---

## v0.1.0 — Initial Build (2026-06-21)

**First release of ReefMind Cloud — the SaaS platform for Neptune Apex aquarium management.**

### Architecture

- **Architected by Archie** — Full multi-tenant SaaS design documented in `docs/saas-architecture-review.md`
- **Built by Cody** — Implementation following `docs/saas-implementation-plan.md`
- **Forked from** [ReefMind](https://github.com/niveknow/ReefMind) (local on-premise project)

### What's Included

#### Backend API (`api/`)
- FastAPI application with auth (JWT + API key), ingest, telemetry, fusion sync, and settings routers
- PostgreSQL models for users, tenants, and tenant config
- InfluxDB write/query service with per-tenant bucket isolation
- Fusion data collector (5-minute background poll) for probe readings and outlet states
- Fusion live data client and controller discovery service
- Nemo AI reef assistant endpoint

#### Frontend (`web/`)
- React + TypeScript + Vite dashboard with ECharts time-series charts
- Login, Register, Dashboard, Settings, and CSV Import pages
- Real-time outlet state grid
- Nemo AI chat widget

#### Infrastructure
- Docker Compose stack: Postgres 16 + InfluxDB 2.7 + Redis 7 + API + Web + Nginx
- Health checks on all services

### Implementation Deltas (Design → Built)

| Design (Archie) | Implementation (Cody) | Rationale |
|-----------------|----------------------|-----------|
| `backend/app/db/models/` structure | `api/app/models/` + `routers/` + `services/` | Flattened structure for small-team velocity |
| Separate on-prem agent container | Server-side Fusion poller (`collector.py` in API lifespan) | Fusion API provides same data; no user-deployed agent needed |
| ARQ Redis-backed async workers | Inline asyncio tasks + synchronous CSV processing | Simpler MVP; ARQ deferred |
| Grafana-compatible dashboards | Custom React + ECharts dashboards | Multi-tenant SaaS needs own UI |
| Fusion API not initially scoped | Full Fusion integration (discovery, live data, history, outlets) | Required for proper data collection without local agent |
| Basic Nemo AI integration | Enhanced Nemo with tank-specific relevance, Fusion context, 60s cache, multi-provider | Rich user experience from MVP |

### Known Limitations
- On-prem agent (standalone Docker container) not yet built — collector runs inside the API container
- No SSL/HTTPS — configured for local dev only
- No billing or Stripe integration
- No alert rules or notification system
