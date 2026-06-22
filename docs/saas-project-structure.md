# ReefMind SaaS — Project Structure

> **Updated:** v0.1.0 implementation uses a simplified `api/app/` layout with unified routers/services rather than per-domain subpackages. See **Implementation Notes** at bottom.

```
ReefMind-Cloud/
├── docker-compose.yml              # Cloud stack (Postgres + InfluxDB + Redis + API + Web)
├── .env.example                    # Cloud stack env vars
│
├── api/                            # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI entry point + lifespan (Fusion collector)
│       ├── config.py               # pydantic-settings config (REEFMIND_ prefix)
│       ├── database.py             # SQLAlchemy async engine + session
│       │
│       ├── models/                 # SQLAlchemy models (flat, one file per domain)
│       │   ├── __init__.py
│       │   ├── tenant.py           # Tenant + TenantConfig
│       │   ├── user.py             # User accounts (tenant-scoped)
│       │   └── csv_import.py       # CSV import tracking
│       │
│       ├── routers/                # FastAPI route handlers (unified)
│       │   ├── __init__.py
│       │   ├── auth.py             # POST /api/auth/register, /api/auth/login
│       │   ├── ingest.py           # POST /api/ingest/* (agent API key auth)
│       │   ├── telemetry.py        # GET /api/telemetry/summary, /outlets, /{probe}
│       │   ├── tenant_config.py    # GET/PUT /api/tenant/config, /regenerate-key
│       │   ├── csv_import.py       # POST /api/csv/upload, GET /api/csv/imports
│       │   ├── nemo.py             # GET /api/nemo/status, POST /api/nemo/ask
│       │   └── fusion.py           # POST /discover, /save, GET /status, /readings, /history, /outlets
│       │
│       ├── schemas/                # Pydantic request/response models
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── ingest.py
│       │   └── telemetry.py
│       │
│       ├── services/               # Business logic layer
│       │   ├── __init__.py
│       │   ├── auth.py             # Password hashing (bcrypt), JWT (HS256), API key gen
│       │   ├── influx.py           # InfluxDB client, per-tenant buckets, write/query
│       │   ├── collector.py        # 5-min Fusion poll loop (asyncio, runs in lifespan)
│       │   ├── fusion_live.py      # Fusion API HTTP client (readings, outlets, outlets-detail)
│       │   └── fusion_discovery.py # Fusion login + controller discovery
│       │
│       └── middleware/
│           ├── __init__.py
│           └── auth.py             # JWT (Bearer) + API Key (X-API-Key) auth dependency
│
│   (Note: migrations/ is not yet present — tables are created via Base.metadata.create_all)
│
├── web/                            # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile                  # Multi-stage: Vite build → Nginx serve
│   ├── nginx.conf                  # Serves static build, proxies /api/* to FastAPI
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                 # React Router: /login, /register, /dashboard, /settings, /csv-import
│       ├── api/
│       │   ├── client.ts           # Axios wrapper with JWT from localStorage
│       │   ├── auth.ts
│       │   ├── dashboard.ts
│       │   ├── tenant.ts
│       │   └── csv.ts
│       ├── components/
│       │   ├── charts/
│       │   │   ├── TimeSeriesChart.tsx  # ECharts time-series (temp, pH, ORP, salinity)
│       │   │   ├── ProbeCards.tsx       # Current readings card grid
│       │   │   ├── OutletGrid.tsx       # ON/OFF outlet state grid
│       │   │   └── NemoWidget.tsx       # Floating AI chat widget
│       │   └── layout/
│       │       ├── DashboardLayout.tsx  # Sidebar + header shell
│       │       └── Sidebar.tsx
│       └── pages/
│           ├── LoginPage.tsx
│           ├── RegisterPage.tsx
│           ├── DashboardPage.tsx        # Main dashboard with probe cards + charts + outlets
│           ├── SettingsPage.tsx         # Fusion config + Nemo AI key + agent key
│           └── CsvImportPage.tsx        # Upload + column mapping preview
│
├── docs/
│   ├── saas-architecture-review.md     # Archie's full architecture design (v2)
│   ├── saas-implementation-plan.md     # Cody's phase-by-phase build plan
│   ├── saas-project-structure.md       # This file
│   └── ANALYSIS-BACKLOG.md             # 15-item feature backlog
│
├── ARCHITECTURE.md                     # Quick-start architecture reference
├── README.md                           # Project overview + setup
├── CHANGELOG.md                        # Release history
├── LICENSE                             # MIT
└── .gitignore
```

---

## Implementation Notes

### Structure Changes from Original Design

The original design (`docs/saas-architecture-review.md` and `docs/saas-implementation-plan.md`) specified a more granular `backend/app/` structure with separate `db/`, `auth/`, `tenants/`, `ingest/`, `dashboard/`, `csv_import/`, and `workers/` subpackages. During implementation, the structure was flattened to the current `api/app/` layout:

- **Routers** are unified under `routers/` instead of per-domain subpackages
- **Services** handle domain logic in `services/` instead of being spread across domain dirs
- **Auth** is handled by `middleware/auth.py` + `services/auth.py` instead of a dedicated `auth/` subpackage
- **No worker subpackage** — background collection runs as an async task in `services/collector.py`

### Removed from Original Structure

The following items from the original design are not yet implemented:

- `migrations/` (Alembic) — schema is created via `Base.metadata.create_all` at startup
- `tests/` (`test_auth.py`, `test_ingest.py`, etc.) — not yet created
- `agent/` directory — separate on-prem agent Docker container and config
- ARQ/Celery worker entry point
