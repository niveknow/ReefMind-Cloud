# Changelog

## v0.1.0 — Initial Build (2026-06-21)

**First release of ReefMind Cloud — the SaaS platform for Neptune Apex aquarium management.**

### Architecture

- **Architected by Archie** — Full multi-tenant SaaS design documented in `docs/saas-architecture-review.md`
- **Built by Cody** — Implementation following `docs/saas-implementation-plan.md`
- **Forked from** [ReefMind](https://github.com/niveknow/ReefMind) (local on-premise project)

### Implementation Deltas (Design → Built)

The following changes were identified during initial testing and are reflected in the updated documentation:

| Design (Archie) | Implementation (Cody) | Rationale |
|-----------------|----------------------|-----------|
| `backend/app/db/models/` structure | `api/app/models/` + `routers/` + `services/` | Flattened structure for small-team velocity |
| Separate on-prem agent container | Server-side Fusion poller (`collector.py` in API lifespan) | Fusion API provides same data; no user-deployed agent needed |
| ARQ Redis-backed async workers | Inline asyncio tasks + synchronous CSV processing | Simpler MVP; ARQ deferred |
| Grafana-compatible dashboards | Custom React + ECharts dashboards | Multi-tenant SaaS needs own UI |
| Fusion API not initially scoped | Full Fusion integration (discovery, live data, history, outlets) | Required for proper data collection without local agent |
| Basic Nemo AI integration | Enhanced Nemo with tank-specific relevance, Fusion context, 60s cache, multi-provider | Rich user experience from MVP, identified as high-value during testing |

### What's Included

#### Backend API (`api/`)
- FastAPI application with auth (JWT + API key), ingest, telemetry, fusion sync, and settings routers
- PostgreSQL models for users, tenants, tenant config, and CSV imports
- InfluxDB write/query service with per-tenant bucket isolation
- Fusion data collector (5-minute background poll) for probe readings and outlet states
- Fusion live data client and controller discovery service
- Nemo AI reef assistant endpoint

#### Frontend (`web/`)
- React + TypeScript + Vite dashboard with ECharts time-series charts
- Login, Register, Dashboard, Settings, and CSV Import pages
- Real-time outlet state grid
- Nemo AI chat widget (embedded)

#### Infrastructure
- Docker Compose stack: Postgres 16 + InfluxDB 2.7 + Redis 7 + API + Web + Nginx
- Same stack works for local dev and VPS deployment (env var switch)
- Health checks on all services

#### Documentation
- `docs/saas-architecture-review.md` — Full architecture design by Archie
- `docs/saas-implementation-plan.md` — Build plan by Archie for Cody
- `docs/saas-project-structure.md` — Original project layout
- `docs/ANALYSIS-BACKLOG.md` — 15-item backlog for future development

### Backlog Issues (15 items)

GitHub Issues created and ready for implementation:

| Area | Issues | Description |
|------|--------|-------------|
| ⚡ Fusion Data | #1–#8 | Power monitoring, device grouping, ilog backfill, mlog, non-probe inputs, multi-controller |
| 🛠 Code Quality | #9–#11 | Client deduplication, error handling, debug prints |
| 📊 Frontend | #12, #13, #15 | Outlet detail panel, water test charts, outlet timeline |
| 📦 Schema | #14 | Controller ID tagging for multi-Apex |

### Known Limitations
- On-prem agent (standalone Docker container) not yet built — collector runs inside the API container
- No SSL/HTTPS — configured for local dev only
- No billing or Stripe integration
- No alert rules or notification system
- Nemo is AI-powered but not yet connected to per-tank InfluxDB data
