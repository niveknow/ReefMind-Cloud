# ReefMind SaaS — Project Structure

```
reefmind/
├── docker-compose.yml              # Cloud stack (API + InfluxDB + Postgres + Web)
├── .env.example                    # Cloud stack env vars
│
├── agent/                          # On-prem agent (user deploys on their network)
│   ├── Dockerfile                  # Single image for collector + cron
│   ├── docker-compose.yml          # User-facing: single service, pre-configured
│   ├── collector.py                # Modified apex_unified_scraper (pushes to cloud)
│   ├── fusion_sync.py              # Modified fusion sync (pushes to cloud)
│   ├── agent_shared.py             # Agent-side shared lib (HTTP client, retry, config)
│   └── agent_config.yaml           # User's config (Apex IP, probes, outlets)
│
├── backend/                        # Cloud backend (FastAPI)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings from env vars (pydantic-settings)
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py          # SQLAlchemy async engine + session
│   │   │   ├── base.py             # Declarative base
│   │   │   └── models/             # SQLAlchemy models
│   │   │       ├── __init__.py
│   │   │       ├── tenant.py
│   │   │       ├── user.py
│   │   │       ├── tenant_config.py
│   │   │       └── csv_import.py
│   │   │
│   │   ├── migrations/             # Alembic
│   │   │   ├── alembic.ini
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── jwt.py              # JWT encode/decode
│   │   │   ├── password.py         # bcrypt hashing
│   │   │   ├── dependencies.py     # FastAPI Depends (get_current_user, etc.)
│   │   │   └── router.py           # /api/auth/* endpoints
│   │   │
│   │   ├── tenants/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # Tenant CRUD + API key generation
│   │   │   └── router.py           # /api/tenant/* endpoints
│   │   │
│   │   ├── ingest/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # Write to InfluxDB per-tenant bucket
│   │   │   ├── influx.py           # InfluxDB client factory (per-tenant token)
│   │   │   └── router.py           # /api/ingest/* endpoints
│   │   │
│   │   ├── dashboard/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # Build dashboard JSON from InfluxDB queries
│   │   │   └── router.py           # /api/dashboard/* endpoints
│   │   │
│   │   ├── csv_import/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # Column mapping, async import processing
│   │   │   ├── column_mapper.py    # Ported from apex_csv_import.py patterns
│   │   │   └── router.py           # /api/csv/* endpoints
│   │   │
│   │   └── workers/
│   │       ├── __init__.py
│   │       ├── worker.py           # ARQ/Celery worker entry point
│   │       └── tasks.py            # csv_import_task, fusion_sync_task
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_ingest.py
│       ├── test_dashboard.py
│       └── test_csv_import.py
│
├── web/                            # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── Dockerfile                  # Nginx static build
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts           # Axios/fetch wrapper with JWT
│   │   │   ├── auth.ts             # login, register, refresh
│   │   │   ├── ingest.ts           # (for admin debugging only)
│   │   │   ├── tenant.ts           # get/update config
│   │   │   ├── dashboard.ts        # fetch dashboard data
│   │   │   └── csv.ts              # upload, list imports, confirm mapping
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useDashboard.ts
│   │   │   └── useWebSocket.ts     # Future: live updates
│   │   │
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Onboarding.tsx
│   │   │   └── CsvImport.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── charts/
│   │   │   │   ├── TimeSeriesChart.tsx    # ECharts wrapper: Temp, pH, ORP
│   │   │   │   ├── OutletGrid.tsx         # ON/OFF grid per outlet
│   │   │   │   ├── LatestReadings.tsx     # Current values card row
│   │   │   │   └── WaterTestHistory.tsx   # (stretch) Ca/KH/Mg over time
│   │   │   ├── CsvMappingPreview.tsx      # Preview columns, confirm mapping
│   │   │   └── NemoWidget.tsx             # Embedded Nemo AI chat
│   │   │
│   │   └── lib/
│   │       ├── formats.ts          # Date/number formatting
│   │       └── constants.ts
│   │
│   └── public/
│       └── favicon.svg
│
├── scripts/
│   ├── migrate_data.py             # Export local InfluxDB → cloud ingest API
│   └── seed_tenant.py              # Create first tenant (Kevin's migration)
│
└── docs/
    ├── saas-architecture-review.md  # This design document
    ├── saas-implementation-plan.md  # Phase-by-phase plan for Cody
    └── api-spec.md                 # Full API reference
```
