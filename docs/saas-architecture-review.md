# ReefMind SaaS — Architecture Review & Design

> **Version:** v2 — Revised after Kevin's decisions (Local-first, Dashboard scope, Nemo role)
> **Status:** Historical design reference — see **Delta Notes** below
> **Assumptions documented:** See Sections 9 & 11

---

## Delta Notes (v0.1.0 Implementation)

This document represents the *design intent* authored before implementation. The following implementation deltas were identified during initial testing:

| Design (this doc) | Implementation | Notes |
|---|---|---|
| `backend/app/db/models/` | `api/app/models/` | Flattened structure |
| Local agent collector pushes to cloud | Server-side Fusion poller in API lifespan | See `api/app/services/collector.py` + `fusion_live.py` |
| ARQ Redis-backed workers | Inline asyncio tasks + sync CSV | ARQ deferred to future |
| Grafana-compatible dashboards | Custom React + ECharts | Implemented |
| Fusion API not in initial scope | Full Fusion endpoints: discover, save, readings, history, outlets | Added during build |
| Basic Nemo | Enhanced: relevance detection, Fusion context, 60s cache, multi-provider | Implemented |

**For the definitive project structure and API layout, see:** `ARCHITECTURE.md`, `README.md`, `docs/saas-project-structure.md`

---

## 1. System Boundary Map

### Current State (Local Single-Tenant)

```
┌─────────────────────────────────────┐
│         TrueNAS SCALE Host           │
│                                      │
│  ┌──────────┐   ┌─────────────────┐  │
│  │ ReefMind  │   │  Apex Controller │  │
│  │ Collector │───▶ (192.168.3.26)  │  │
│  │ (60s poll)│   │  status.xml     │  │
│  └─────┬─────┘   └─────────────────┘  │
│        │                              │
│        ▼                              │
│  ┌──────────┐   ┌─────────────────┐  │
│  │ InfluxDB  │   │  Fusion Cloud   │  │
│  │ v2.7      │◀──│  API (cron)     │  │
│  │ telemetry │   └─────────────────┘  │
│  └─────┬─────┘                       │
│        │                              │
│        ▼                              │
│  ┌──────────┐   ┌─────────────────┐  │
│  │ Grafana   │   │  Nemo AI        │  │
│  │ Dashboards│   │  Chat Assistant │  │
│  └──────────┘   └─────────────────┘  │
└─────────────────────────────────────┘
```

### Target State (Cloud Multi-Tenant SaaS)

```
┌─────────────────────────────────────────┐
│               CLOUD (ReefMind SaaS)      │
│                                          │
│  ┌──────────┐    ┌──────────────────┐   │
│  │ Public     │    │  Web App          │   │
│  │ API Gateway│───▶│  (Dashboard +     │   │
│  │ (auth)     │    │   Onboarding)     │   │
│  └─────┬──────┘    └────────┬─────────┘   │
│        │                    │              │
│        ▼                    ▼              │
│  ┌──────────┐    ┌──────────────────┐   │
│  │ Ingest    │    │  Tenant DB       │   │
│  │ API       │    │  (PostgreSQL)    │   │
│  └─────┬──────┘    └──────────────────┘   │
│        │                                   │
│        ▼                                   │
│  ┌──────────────────────────────┐          │
│  │  Time-Series (InfluxDB)      │          │
│  │  ┌─────────┐ ┌──────────┐   │          │
│  │  │tenant_a │ │tenant_b  │...│          │
│  │  │ bucket  │ │ bucket   │   │          │
│  │  └─────────┘ └──────────┘   │          │
│  └──────────────────────────────┘          │
│        │                                    │
│        ▼                                    │
│  ┌──────────────────────────────┐          │
│  │  Background Workers          │          │
│  │  (Fusion sync, CSV import,   │          │
│  │   alert evaluation)          │          │
│  └──────────────────────────────┘          │
└─────────────────────────────────────────┘
                ▲
                │ HTTPS (push)
                │
┌───────────────┴─────────────────────┐
│        USER'S NETWORK                │
│                                      │
│  ┌──────────────────────┐            │
│  │  ReefMind Agent       │            │
│  │  (lightweight Docker  │            │
│  │   container)          │            │
│  └─────────┬────────────┘            │
│            │                          │
│            ▼                          │
│  ┌──────────────────────┐            │
│  │  Apex Controller      │            │
│  │  (local IP, status.xml)│           │
│  └──────────────────────┘            │
└─────────────────────────────────────┘
```

### Local Development Mode (MVP Before VPS)

During development, everything runs on Kevin's TrueNAS (or local machine). The "cloud" and "agent" are all inside the same Docker Compose stack:

```
┌─────────────────────────────────────────────────┐
│              TrueNAS / Local Machine             │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Docker Compose (single host)          │     │
│  │                                         │     │
│  │  ┌────────┐  ┌────────┐  ┌─────────┐  │     │
│  │  │Postgres│  │InfluxDB│  │ Redis    │  │     │
│  │  └───┬────┘  └───┬────┘  └────┬────┘  │     │
│  │      │           │            │       │     │
│  │  ┌───┴───────────┴────────────┴───┐   │     │
│  │  │       FastAPI Backend          │   │     │
│  │  │  (auth, ingest, dash, csv)     │   │     │
│  │  └───────────────┬────────────────┘   │     │
│  │                  │                    │     │
│  │  ┌───────────────┴────────────────┐   │     │
│  │  │     React Web App (Vite)       │   │     │
│  │  │     = Dashboard + Nemo         │   │     │
│  │  └────────────────────────────────┘   │     │
│  │                                         │     │
│  │  ┌────────────────────────────────┐     │     │
│  │  │  Agent (container)             │     │     │
│  │  │  polls Apex → POST /api/ingest*│────│──┐  │
│  │  │  via Docker network (no HTTPS) │     │  │  │
│  │  └────────────┬───────────────────┘     │  │  │
│  └───────────────┼─────────────────────────┘  │  │
│                  │                            │  │
│                  ▼                            │  │
│  ┌──────────────────────────┐                │  │
│  │  Apex Controller          │◀───────────────┘  │
│  │  (192.168.3.26)           │                   │
│  └──────────────────────────┘                   │
└──────────────────────────────────────────────────┘
```

**Key principle:** The same `docker-compose.yml` works for both local development and VPS deployment. Only environment variables differ:
- Locally: `REEFMIND_API_URL=http://api:8000`, no SSL
- VPS: `REEFMIND_API_URL=https://reefmind.io`, SSL via Caddy reverse proxy

The agent connects to the API via Docker internal networking during local dev (no HTTPS needed).

---

## 2. Critical Architecture Decisions

### Decision 1: On-Prem Agent Model

**The fundamental constraint:** The Neptune Apex controller lives on the user's local network (no public IP, no inbound access). The cloud cannot reach it.

**Options considered:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **On-prem agent pushes to cloud API** | Works through NAT/firewall; simple; reuse existing collector code | Requires user to run something on their network | ✅ **MVP choice** |
| Cloud-pull via Fusion API only | No agent needed; user just provides credentials | Fusion only keeps 7 days of data; no real-time polling (Fusion is cached) | ❌ Loses the core value of real-time data |
| VPN/tunneling to Apex | Full cloud control | Complex setup; security risk exposing controller | ❌ Overengineered for MVP |

**Decision:** The on-prem agent model. Users run a lightweight Docker container (or single binary) that polls their Apex controller and pushes telemetry to the ReefMind cloud API. This is essentially the existing `collector` container, modified to push to the cloud instead of writing to a local InfluxDB.

### Decision 2: Tenant Isolation Model

| Approach | Pros | Cons | MVP Verdict |
|----------|------|------|-------------|
| **Per-tenant InfluxDB buckets** | Native InfluxDB isolation; clean separation; easy to manage | Need to ensure bucket creation in API; small overhead | ✅ **MVP choice** |
| Shared bucket + tenant_id tag | Simpler to manage; fewer buckets | Requires careful query filtering; risk of cross-tenant leakage in queries | ❌ Acceptable but weaker isolation |
| Database-per-tenant | Strongest isolation | Complex to manage at scale; overkill for MVP | ❌ Future scale-up path |

**Decision:** Per-tenant InfluxDB buckets with a tenant-scoped auth token. Each bucket is named `reefmind_{tenant_id}`. The agent only knows about its own bucket via the API gateway.

### Decision 3: Relational DB for Non-Timeseries Data

**Need identified:** The current system has no relational store. For SaaS, we need:

- User accounts & authentication
- Tenant configuration (Apex IP, probe list, outlet map, Fusion credentials)
- Billing state (future)
- API tokens & refresh keys
- CSV import job tracking

**Decision:** PostgreSQL for the operational/relational store. InfluxDB stays for telemetry.

### Decision 4: Authentication Model

**Decision:** JWT-based auth with API key fallback for agent push.

| Flow | Mechanism |
|------|-----------|
| Web UI login | Email + password → JWT session |
| Agent-to-cloud push | Per-tenant API key (long-lived, rotational) |
| Public API scoping | Enforced at API Gateway via tenant_id from JWT/API key |

### Decision 5: Dashboard (Replacing Grafana)

**The Grafana problem:** Grafana is architected as a single-tenant tool. Running it as a multi-tenant SaaS would require Grafana's "service account" per user pattern, which is brittle.

**Options:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Custom web dashboard (React + ECharts)** | Full control; multi-tenant from day 1; exactly what we need | Development effort to replicate Grafana panels | ✅ **MVP choice** |
| Hosted Grafana with per-user orgs | Familiar UI | Grafana multi-tenancy is complex; heavy infra; license constraints | ❌ Too heavy for MVP |
| Embed Grafana panels via iframe | Quick win | Authentication jank; limited customization | ❌ Hacky |
| Redash / Metabase | Purpose-built for multiple users | Still requires separate infra; feels heavy | ❌ |

**Dashboard strategy (from the existing `modern-reef-dashboard.json`):**

The custom React dashboard should mirror the existing Grafana dashboard as closely as possible. The Grafana JSON is the spec — every panel in that file should have a corresponding component in the web UI.

**Community dashboard sharing:** Users can export their dashboard layout as JSON (Grafana-compatible format) and share it with the community. The import feature accepts both:
- Native ReefMind JSON format
- Standard Grafana JSON (stripped of Grafana-specific keys, mapped to ReefMind's data sources)

This means the custom dashboard is built with a **panel schema** that maps to the Grafana panel structure, making community import/export natural.

### Decision 7: Nemo AI — General Reef Advisor (MVP)

**Kevin's direction:** Nemo should start as a general reef-keeping knowledge assistant, not a per-tank AI. The premium paid tier (future) will add per-tank personalization (reading the tenant's InfluxDB data for context-aware answers).

| Aspect | MVP (General Advisor) | Premium Tier (Future) |
|--------|----------------------|----------------------|
| Knowledge source | reef2reef.com corpus, general reefing knowledge | Same + tenant's own InfluxDB telemetry + fusion notes |
| Can answer | "What temp should my SPS tank be?" | "Why did my pH drop 0.3 at 3am yesterday?" |
| Data access | None (no InfluxDB read scope) | Reads tenant's InfluxDB bucket |
| Architecture | Static Q&A with RAG on reef2reef content | RAG + InfluxDB query capability |
| Cost | Fixed (controlled knowledge base size) | Variable (per-token per tenant) |

**Implementation approach for MVP:** Nemo is a standalone AI chat widget that knows reefing best practices. It can be pre-seeded with content from reef2reef.com via a static knowledge base or a simple retrieval system. No tenant InfluxDB access required.

|  **Nemo is embedded in the web dashboard** as a floating chat bubble, same as it is currently in the Grafana dashboard.

### Decision 8: Technology Stack

| Layer
|-------|-----------|-----------|
| **Backend API** | FastAPI (Python) | Same language as existing collectors; proven async framework; auto-docs |
| **Web UI** | React + Vite + Tailwind | Fast; good ecosystem; easy to iterate |
| **Dashboard charts** | Apache ECharts (via lightweight wrapper) | Mature; handles time-series well; no React-heavy chart library lock-in |
| **Relational DB** | PostgreSQL (via SQLAlchemy + Alembic) | Industry standard; great tooling |
| **Time-series DB** | InfluxDB OSS v2.x (hosted or self-managed) | Already proven in the current stack; influxdb-client-python already used |
| **Agent** | Python (same codebase, modified output target) | Reuse 90% of existing `apex_unified_scraper.py` |
| **Auth** | JWT (PyJWT) + bcrypt | Simple; no external auth provider dependency for MVP |
| **Async workers** | Celery or ARQ (Redis-backed) | Fusion sync jobs, CSV import processing |
| **Deployment** | Docker Compose (MVP) → Kubernetes (scale) | Familiar; easy iteration |

---

## 3. Data Model

### Relational (PostgreSQL) — New

```sql
-- Core tenant and user model
tenants:
  id              UUID PK
  name            VARCHAR       -- e.g. "Kevin's 180G Reef"
  slug            VARCHAR UNIQ  -- URL-safe identifier
  created_at      TIMESTAMP
  status          VARCHAR       -- active | trialing | suspended

users:
  id              UUID PK
  tenant_id       UUID FK → tenants
  email           VARCHAR UNIQ
  password_hash   VARCHAR
  role            VARCHAR       -- admin | member
  created_at      TIMESTAMP

tenant_configs:
  id              UUID PK
  tenant_id       UUID FK → tenants
  backend_type    VARCHAR       -- "apex" (future: "profilux", "hydros")
  config_json     JSONB         -- full backend config (host, outlets, probes, etc.)
  fusion_user     VARCHAR       -- encrypted at rest
  fusion_pass     VARCHAR       -- encrypted at rest
  fusion_apex_id  VARCHAR
  agent_api_key   VARCHAR       -- long-lived key for agent auth
  created_at      TIMESTAMP
  updated_at      TIMESTAMP

-- Future: billing_subscriptions, api_tokens, alert_rules
```

### Time-Series (InfluxDB) — Existing Schema, Tenant-Scoped

The existing measurements are preserved. Each tenant gets their own bucket `reefmind_{tenant_id}`:

```
apex_telemetry:
  tags:    tenant_id, probe_name, probe_type, unit
  fields:  value
  Example: Temp=78.3, pH=8.12, ORP=380, Salt=35.2

apex_outlet_states:
  tags:    tenant_id, outlet_name
  fields:  state (int), state_display (string)
  Example: MainPump=1 (ON), Skimmer=1 (ON)

apex_water_tests:
  tags:    tenant_id, parameter, unit
  fields:  value
  Example: KH=8.4, Ca=420, Mg=1350

apex_power:
  tags:    tenant_id, outlet_name, channel
  fields:  watts, amps
  Example: MainPump=45.2W
```

### CSV Import — New Table

```sql
csv_imports:
  id              UUID PK
  tenant_id       UUID FK → tenants
  filename        VARCHAR
  file_size       INTEGER
  rows_imported   INTEGER
  rows_skipped    INTEGER
  status          VARCHAR       -- pending | processing | completed | failed
  error_message   TEXT
  column_mapping  JSONB         -- user-confirmed header→measurement mapping
  created_at      TIMESTAMP
  completed_at    TIMESTAMP
```

---

## 4. API Surface (MVP)

```
POST   /api/auth/register                  # Create account + tenant
POST   /api/auth/login                     # Get JWT
POST   /api/auth/refresh                   # Refresh JWT

GET    /api/tenant/config                  # Current tenant's config
PUT    /api/tenant/config                  # Update config (probes, outlets, etc.)
POST   /api/tenant/regenerate-agent-key    # Rotate agent API key

POST   /api/ingest/telemetry              # Agent pushes probe data (API-key auth)
POST   /api/ingest/outlets                 # Agent pushes outlet states
POST   /api/ingest/power                   # Agent pushes power data
POST   /api/ingest/water-tests             # Agent pushes manual test results

POST   /api/csv/upload                     # Upload CSV for import
GET    /api/csv/imports                    # List import history
GET    /api/csv/imports/:id                # Import details
POST   /api/csv/imports/:id/confirm        # Confirm column mapping, start import
DELETE /api/csv/imports/:id                # Cancel/delete import

GET    /api/telemetry/:probe               # Query probe data (Time range)
GET    /api/telemetry/summary              # Latest readings for all probes
GET    /api/outlets/state                  # Current outlet states
GET    /api/power/current                  # Current power readings
GET    /api/power/history                  # Power usage over time

GET    /api/dashboard/summary              # Pre-built dashboard data (1 call = all panels)

# Future:
# POST   /api/fusion/sync                   # Trigger Fusion sync
# POST   /api/alerts                        # CRUD alert rules
# POST   /api/billing                        # Stripe integration
```

---

## 5. Agent Architecture

The on-prem agent is a repackaged version of the existing collector + cron containers, but instead of writing to a local InfluxDB, it calls the cloud ingest API.

### Agent Containers (user runs on their hardware)

```
reefmind-agent/
├── collector/               # Modified apex_unified_scraper.py
│   └── → polls Apex → POSTs /api/ingest/telemetry + outlets + power
├── fusion-sync/             # Modified fusion sync scripts
│   └── → syncs from Fusion API → POSTs /api/ingest/telemetry
├── csv-import/              # Uploads CSV to cloud for processing
│   └── → POST /api/csv/upload (file upload)
└── docker-compose.yml       # Single-file deploy for user
```

**Key difference from current:** The agent is stateless — it doesn't run InfluxDB or Grafana locally. It just collects and pushes. This makes it dramatically lighter.

**User setup flow:**
1. Sign up at reefmind.io
2. Complete onboarding form (Apex IP, probes, outlets, Fusion credentials)
3. Receive `docker-compose.yml` with their tenant API key pre-filled
4. Run `docker compose up -d` on their local machine
5. Data starts flowing to the cloud

### Agent Security Model

- Agent API key is scoped to a single tenant
- Agent can only write to ingest endpoints
- No read access to other tenants' data
- API key rotation is a config update + regenerate
- All agent → cloud traffic over HTTPS

---

## 6. Ingress & Data Flow

```
USER's NETWORK                    CLOUD
                                  ┌────────────────────────┐
┌─────────────┐                   │  API Gateway (Nginx/Caddy) │
│ Agent        │──HTTPS POST────▶│  ├── /api/ingest/*        │
│ (collector)  │   /ingest/*      │  └── /api/* (JWT required)│
└─────────────┘                   └───────────┬────────────┘
                                              │
                                              ▼
                                     ┌────────────────────┐
                                     │  FastAPI Backend    │
                                     │                    │
                                     │  - Auth middleware  │
                                     │  - Tenant resolver  │
                                     │  - Write to Influx  │
                                     │  - Queue workers    │
                                     └─────────┬──────────┘
                                               │
                                  ┌────────────┴────────────┐
                                  ▼                         ▼
                          ┌──────────────┐       ┌────────────────┐
                          │  InfluxDB     │       │  PostgreSQL     │
                          │  per-tenant   │       │  (users, config,│
                          │  buckets      │       │   imports, etc.)│
                          └──────────────┘       └────────────────┘
                                               │
                                               ▼
                                        ┌────────────────────┐
                                        │  Web App (React)    │
                                        │  - Dashboard        │
                                        │  - Settings         │
                                        │  - CSV import UI    │
                                        │  - Nemo AI Chat     │
                                        └────────────────────┘
```

---

## 7. MVP Scope — Phase 0

**Goal:** Get from local single-tenant → working cloud SaaS with 1 beta user (Kevin) within 2-3 weeks.

### In MVP

| Component | Scope | Effort |
|-----------|-------|--------|
| **Agent** | Repackage existing collector to push to cloud API instead of local InfluxDB | Low (mostly config changes + HTTP client) |
| **Auth** | Register/login flow, JWT session, API key generation | Low |
| **Ingest API** | 4 endpoints (telemetry, outlets, power, water-tests) + InfluxDB per-tenant write | Low |
| **Dashboard** | Full mirror of the existing `modern-reef-dashboard.json`: Temp, pH, ORP, Salt line charts, outlet ON/OFF grid, power consumption, water test history. Community dashboard JSON import/export. | Medium-High |
| **Tenant config** | Web form to configure Apex IP, probes, outlets, Fusion creds | Medium |
| **Nemo** | General reef advisor (knowledge base, no per-tank data access). Embedded chat widget in dashboard. | Medium |
| **CSV Import** | Upload CSV, auto-detect column mapping (ported from apex_csv_import.py), confirm, write to InfluxDB | Medium |
| **Deployment** | Single Docker Compose that runs locally (TrueNAS) AND on VPS with env var switch | Low |

### Out of MVP

| Component | Rationale |
|-----------|-----------|
| Billing/Stripe | Free during beta. Don't build until you need to charge. |
| Alert rules / notifications | Important but not v1. Manual monitoring during beta. |
| Team/multi-user per tenant | Beta users are solo operators. |
| Admin panel (view all tenants) | Can use direct DB access during beta. |
| Fusion auto-sync scheduling | Agent can trigger from its own cron. Cloud triggers later. |
| Public landing page | A simple login page + app is fine for beta. |
| Mobile app | Web dashboard is responsive enough for MVP. |
| Anomaly detection | Future ML feature. Nemo can answer ad-hoc questions. |

---

## 8. Migration Path for Kevin's Existing Data

**Goal:** Kevin's historical InfluxDB data is preserved and migrated to the cloud.

1. Deploy cloud stack (empty)
2. Run migration script locally: export data from local InfluxDB bucket → POST to cloud ingest API with backdated timestamps
3. Start the agent → real-time data starts flowing
4. Stop local Docker Compose stack (InfluxDB + Grafana stay as read-only backup)
5. Verify dashboard matches on cloud

The `apex_csv_import.py` tool already has the column mapping and InfluxDB write logic. The migration script essentially becomes:
- Read from local InfluxDB via Flux query
- Batch-write to cloud `/api/ingest/telemetry`

---

## 9. Confirmed Decisions (from Kevin)

| Question | Decision | Implication |
|----------|----------|-------------|
| Agent deployment format | Docker Compose | Agent ships as Docker Compose. Kevin will test on his TrueNAS Scale as a simulated customer deploy. |
| Cloud hosting timing | VPS determined later. MVP must run locally first. | The entire cloud stack (Postgres, InfluxDB, Redis, API, Web) must be demonstrable on Kevin's local machine. Same Docker Compose works locally and on VPS. |
| Dashboard scope | Full mirror of `modern-reef-dashboard.json` | Build all panels from the existing Grafana dashboard. Support community dashboard JSON import/export (Grafana-compatible format). |
| Nemo AI role | General reef advisor (reef2reef knowledge) | Nemo knows reefing best practices but not tank-specific data. Per-tank personalization is a future premium tier. |

## 10. Local-First Development Sequence

```
Step 1:  Build cloud stack + run locally on TrueNAS  ← we are here
         (Postgres + InfluxDB + Redis + API + Web)
         Agent connects via Docker network (http://api:8000)
         → All SaaS features work on localhost

Step 2:  Kevin demos MVP locally
         → Register account, configure tank, see dashboard live

Step 3:  Provision VPS, deploy same docker-compose.yml
         → Add Caddy reverse proxy + Let's Encrypt SSL
         → Change REEFMIND_API_URL to the VPS domain

Step 4:  First external beta user
         → They install agent Docker Compose, point at VPS URL
         → Cloud now multi-tenant with real external data
```

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fusion API credentials expose user accounts | Low | High | Encrypt credentials at rest in PostgreSQL; agent never stores them, only the cloud cron does |
| Agent-to-cloud latency causes data gaps | Medium | Low | Agent buffers last N failed writes and retries; ingest API accepts batch writes |
| Multi-tenant InfluxDB performance degrades | Low (MVP scale) | Medium | Each tenant has their own bucket; InfluxDB handles thousands of buckets well |
| CSV import of large files (years of data) times out | Medium | Low | Async worker (Celery/ARQ) processes imports; user sees progress bar |
| Nemo AI costs at scale | Medium | Medium | Track token usage per tenant from day 1; rate-limit free tier |
| Dashboard reimplementation misses edge cases from Grafana | Medium | Medium | Keep Grafana dashboard JSON as reference spec; compare panel-by-panel during QA |
