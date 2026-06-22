# Changelog

## v0.1.0 — Initial Build (2026-06-21)

**First release of ReefMind Cloud — the SaaS platform for Neptune Apex aquarium management.**

### Architecture

- **Architected by Archie** — Full multi-tenant SaaS design documented in `docs/saas-architecture-review.md`
- **Built by Cody** — Implementation following `docs/saas-implementation-plan.md`
- **Forked from** [ReefMind](https://github.com/niveknow/ReefMind) (local on-premise project)

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
