# ReefMind SaaS — Implementation Plan

> **Target:** Cody (Developer Agent)
> **Source:** Archie (SaaS Architect)
> **Goal:** Turn ReefMind from a local single-tenant Docker app into a multi-tenant cloud SaaS
> **Status:** Historical build plan — see **Delta Notes** below

---

## Delta Notes (v0.1.0 Implementation)

This plan was the build specification. The following deltas reflect decisions made during implementation:

| Plan Item | Built Status | Notes |
|-----------|-------------|-------|
| Phase 0: Backend scaffold | ✅ **Built** — Simplified to `api/app/` layout | See `docs/saas-project-structure.md` |
| Phase 0: Database models | ✅ **Built** — 3 models (User, Tenant+TenantConfig, CsvImport) | No migrations yet — uses `create_all` |
| Phase 0: Auth | ✅ **Built** — JWT (HS256) + API key bearer | Auth middleware at `middleware/auth.py` |
| Phase 1: Ingest API | ✅ **Built** — `/api/ingest/telemetry`, `/outlets`, `/power` | Agent API key auth |
| Phase 1: Telemetry API | ✅ **Built** — `/api/telemetry/summary`, `/outlets`, `/{probe}` | JWT auth |
| ARQ worker queue | 🔄 **Deferred** — Synchronous/async inline | Fusion collector runs in API lifespan |
| Separate agent container | 🔄 **Deferred** — Server-side Fusion collection | See `services/collector.py` + `fusion_live.py` |
| Fusion live data API | ⭐ **Added (not in original plan)** | `/api/fusion/*` — discovery, readings, history, outlets |
| Nemo AI | ⭐ **Enhanced beyond plan** — Relevance detection, Fusion context, caching, multi-provider | `/api/nemo/ask` + `/api/nemo/status` |
| Alembic migrations | ❌ **Not yet** | Schema created via `Base.metadata.create_all` |
| Test suite | ❌ **Not yet** | Pending — Trixie will create test plans

---

## Assumptions

These decisions were made by Kevin. They drive the entire build.

| Decision | Value | Rationale |
|----------|-------|-----------|
| Agent format | Docker Compose | Kevin will test on his TrueNAS Scale as simulated customer deploy |
| VPS timing | After MVP is working locally | No cloud spend until the product is validated |
| Dashboard scope | Full `modern-reef-dashboard.json` mirror + community JSON import/export | Users can share dashboard layouts (Grafana-compatible format) |
| Nemo role | General reef advisor (reef2reef knowledge base) | Per-tank personalization = future premium tier |
| Auth model | JWT + per-tenant API key (no OAuth provider) | Keep it simple |
| Async worker | ARQ (Redis-backed) | Lighter than Celery |
| Deploy model | Single Docker Compose for both local + VPS (env var switch) | Zero rework when moving to VPS |

---

## Data Flow

### Local Development (MVP — Kevin's TrueNAS)

```
┌───────────────────────────────────────────────────────┐
│                   TrueNAS SCALE Host                    │
│                                                         │
│  ┌───────────────────┐                                 │
│  │  Apex Controller   │                                 │
│  │  192.168.3.26      │                                 │
│  └────────┬──────────┘                                 │
│           │ status.xml (http, LAN)                      │
│  ┌────────▼─────────────────────────────────────────┐  │
│  │              Docker Compose Stack                  │  │
│  │                                                    │  │
│  │  ┌──────────┐                                     │  │
│  │  │  Agent    │  polls Apex → POST /api/ingest/*   │  │
│  │  │  (Python) │──http://api:8000 (Docker network)─▶│  │
│  │  └──────────┘                                     │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │            FastAPI Backend                    │  │  │
│  │  │  /api/ingest/*, /api/auth/*, /api/dashboard  │  │  │
│  │  │  /api/csv/*, /api/tenant/*                   │  │  │
│  │  └────────┬──────────┬──────────┬───────────────┘  │  │
│  │           │          │          │                    │  │
│  │  ┌────────▼──┐ ┌────▼────┐ ┌───▼────────┐         │  │
│  │  │ Postgres   │ │InfluxDB │ │  Redis     │         │  │
│  │  │ :5432      │ │ :8086   │ │  :6379     │         │  │
│  │  └───────────┘ └─────────┘ └────────────┘         │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │   React Web App (Vite dev or Nginx static)   │  │  │
│  │  │   :80 → /dashboard → /settings → /csv-import │  │  │
│  │  │   :80 → / (Nemo chat widget floating)         │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### VPS Deployment (Same Docker Compose, env vars differ)

```
USER NETWORK                   VPS (Caddy + SSL)
┌──────────────┐               ┌─────────────────────────────┐
│ Agent         │──HTTPS──▶    │ *.reefmind.io:443            │
│ (own Docker)  │  POST /ingest│ └→ Caddy → FastAPI            │
│               │              │                               │
│ Browser       │──HTTPS──▶    │ reefmind.io:443               │
│               │  Web UI     │ └→ Caddy → React SPA          │
└──────────────┘               └─────────────────────────────┘
```

**Env variables that change between local and VPS:**
```
# Local
REEFMIND_API_URL=http://api:8000
REEFMIND_WEB_URL=http://localhost:80
ENABLE_SSL=false

# VPS
REEFMIND_API_URL=https://api.reefmind.io
REEFMIND_WEB_URL=https://reefmind.io
ENABLE_SSL=true
```

---

## Phase 0: Project Scaffolding & Shared Backend

**Goal:** Get the cloud backend project structure in place with database models, migrations, and the FastAPI skeleton running.

### Task 0.1 — Create backend project skeleton

```bash
# From reefmind/
mkdir -p backend/app/{db/models,auth,tenants,ingest,dashboard,csv_import,workers}
mkdir -p backend/tests
mkdir -p backend/app/migrations/versions
touch backend/app/__init__.py
touch backend/app/db/__init__.py
touch backend/app/db/models/__init__.py
touch backend/app/auth/__init__.py
touch backend/app/tenants/__init__.py
touch backend/app/ingest/__init__.py
touch backend/app/dashboard/__init__.py
touch backend/app/csv_import/__init__.py
touch backend/app/workers/__init__.py
```

**Files to create:**

1. **`backend/requirements.txt`** — FastAPI, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, pyjwt, bcrypt, influxdb-client, python-multipart, httpx, arq, redis

2. **`backend/app/config.py`** — pydantic-settings `Settings` class reading from env:
   ```
   DATABASE_URL (postgresql+asyncpg://...)
   INFLUXDB_URL
   INFLUXDB_ORG
   INFLUXDB_ADMIN_TOKEN
   REDIS_URL
   JWT_SECRET
   JWT_ALGORITHM=HS256
   JWT_EXPIRY_HOURS=72
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   AGENT_API_KEY_LENGTH=48
   ```

3. **`backend/app/main.py`** — Minimal FastAPI app with CORS, lifespan (db pool), mount routers.

4. **`backend/app/db/base.py`** — SQLAlchemy `DeclarativeBase`

5. **`backend/app/db/session.py`** — Async engine + `get_db()` dependency

6. **`backend/app/db/models/tenant.py`**
   ```python
   class Tenant(Base):
       __tablename__ = "tenants"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid4)
       name: Mapped[str]
       slug: Mapped[str] = mapped_column(unique=True, index=True)
       status: Mapped[str] = mapped_column(default="active")  # active, trialing, suspended
       created_at: Mapped[datetime] = mapped_column(default=func.now())
       updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
       # Relationships
       users: Mapped[list["User"]] = relationship(back_populates="tenant")
       config: Mapped[list["TenantConfig"]] = relationship(back_populates="tenant")
   ```

7. **`backend/app/db/models/user.py`**
   ```python
   class User(Base):
       __tablename__ = "users"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid4)
       tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
       email: Mapped[str] = mapped_column(unique=True, index=True)
       password_hash: Mapped[str]
       display_name: Mapped[str]
       role: Mapped[str] = mapped_column(default="admin")  # admin, member
       created_at: Mapped[datetime] = mapped_column(default=func.now())
       tenant: Mapped["Tenant"] = relationship(back_populates="users")
   ```

8. **`backend/app/db/models/tenant_config.py`**
   ```python
   class TenantConfig(Base):
       __tablename__ = "tenant_configs"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid4)
       tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), unique=True)
       backend_type: Mapped[str] = mapped_column(default="apex")
       config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
       fusion_user: Mapped[Optional[str]]
       fusion_pass_encrypted: Mapped[Optional[str]]
       fusion_apex_id: Mapped[Optional[str]]
       agent_api_key_hash: Mapped[Optional[str]]
       created_at: Mapped[datetime] = mapped_column(default=func.now())
       updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
       tenant: Mapped["Tenant"] = relationship(back_populates="config")
   ```

9. **`backend/app/db/models/csv_import.py`**
   ```python
   class CsvImport(Base):
       __tablename__ = "csv_imports"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid4)
       tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
       filename: Mapped[str]
       file_size: Mapped[int]
       rows_imported: Mapped[int] = mapped_column(default=0)
       rows_skipped: Mapped[int] = mapped_column(default=0)
       status: Mapped[str] = mapped_column(default="pending")
       error_message: Mapped[Optional[str]]
       column_mapping: Mapped[Optional[dict]] = mapped_column(JSONB)
       storage_path: Mapped[Optional[str]]
       created_at: Mapped[datetime] = mapped_column(default=func.now())
       completed_at: Mapped[Optional[datetime]]
   ```

10. **`backend/app/migrations/`** — Alembic init + initial migration auto-generated

### Task 0.2 — Docker Compose for Cloud Stack

**`docker-compose.yml`** at project root:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env: POSTGRES_DB=reefmind, POSTGRES_USER=reefmind, POSTGRES_PASSWORD=...
    volumes: pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  influxdb:
    image: influxdb:2.7-alpine
    env: DOCKER_INFLUXDB_INIT_MODE=setup, DOCKER_INFLUXDB_INIT_ORG=reefmind, ...
    volumes: influxdb_data:/var/lib/influxdb2
    ports: ["8086:8086"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: ./backend
    env: DATABASE_URL, INFLUXDB_URL, JWT_SECRET, REDIS_URL, ...
    ports: ["8000:8000"]
    depends_on: [postgres, influxdb, redis]

  web:
    build: ./web
    ports: ["80:80"]
    depends_on: [api]

  worker:
    build: ./backend
    command: arq app.workers.worker.Worker
    env: same as api
    depends_on: [postgres, influxdb, redis]
```

### Task 0.3 — InfluxDB Bootstrap on Startup

Create `backend/app/ingest/influx.py` with a bootstrap function that:
- Connects to InfluxDB using admin token
- Creates the org `reefmind` if not exists
- Creates per-tenant buckets lazily: `reefmind_{tenant_id}` when a new tenant registers
- Returns a tenant-scoped write API client from tenant token

**Function:**
```python
async def ensure_tenant_bucket(tenant_id: str) -> str:
    """Create bucket reefmind_{tenant_id} if not exists. Return the bucket name."""
    # Uses InfluxDB admin token
    # Creates org: reefmind
    # Creates bucket: reefmind_{tenant_id} if not present

async def get_influx_client(tenant_id: str):
    """Return a write client scoped to this tenant's bucket."""
    bucket = await ensure_tenant_bucket(tenant_id)
    # Create a read/write token for this tenant, or use admin for now (MVP)
    ...
```

---

## Phase 1: Authentication & Tenant Management

**Goal:** Users can register, log in, and manage their tenant configuration.

### Task 1.1 — JWT Auth Module

Create `backend/app/auth/`:

- **`jwt.py`**: `create_access_token(user_id, tenant_id, role)`, `decode_token(token)`
- **`password.py`**: `hash_password(plain)`, `verify_password(plain, hash)`
- **`dependencies.py`**: `get_current_user()` FastAPI dependency that validates JWT from `Authorization: Bearer` header and returns `(user_id, tenant_id, role)`

### Task 1.2 — Auth Router (`/api/auth/*`)

**`register`:**
- Accepts `email, password, display_name, tenant_name`
- Creates Tenant (slug from tenant_name, sanitized)
- Creates User with hashed password
- Creates TenantConfig with default Apex config
- Generates and stores agent API key
- Returns JWT + agent API key (shown once, like a setup key)

**`login`:**
- Accepts `email, password`
- Verifies credentials
- Returns JWT

**`refresh`:**
- Accepts valid JWT
- Returns new JWT

**Agent API key auth** — separate dependency for ingest routes:
```python
async def verify_agent_api_key(authorization: str = Header(...)) -> str:
    """Returns tenant_id from the API key. Used by /api/ingest/* routes."""
    # Look up key hash in tenant_configs
    # Return tenant_id
```

### Task 1.3 — Tenant Config Router (`/api/tenant/*`)

**`GET /api/tenant/config`:**
- Returns current tenant's config (backend_type, config_json — without secrets)

**`PUT /api/tenant/config`:**
- Accepts updated config JSON (probes, outlets, fusion_url, etc.)
- Updates TenantConfig in DB
- Returns updated config

**`POST /api/tenant/regenerate-agent-key`:**
- Generates new API key
- Stores hash in DB
- Returns plaintext key (shown once)

---

## Phase 2: Ingest API & Agent

**Goal:** Existing collector code can push data to the cloud.

### Task 2.1 — Ingest API Endpoints

Create `backend/app/ingest/`:

**`POST /api/ingest/telemetry`** — verified by agent API key:
```json
{
  "points": [
    {
      "time": "2026-06-21T12:00:00Z",   // optional, server uses now if absent
      "probe_name": "Temp",
      "probe_type": "Temp",
      "unit": "F",
      "value": 78.3
    },
    {
      "probe_name": "pH",
      "probe_type": "pH",
      "unit": "pH",
      "value": 8.12
    }
  ]
}
```
→ Writes to InfluxDB bucket `reefmind_{tenant_id}`, measurement `apex_telemetry`.

**`POST /api/ingest/outlets`:**
```json
{
  "outlets": [
    {"name": "MainPump", "state": 1, "state_display": "ON"},
    {"name": "Skimmer", "state": 1, "state_display": "ON"}
  ]
}
```
→ Writes to measurement `apex_outlet_states`.

**`POST /api/ingest/power`:**
```json
{
  "readings": [
    {"outlet": "MainPump", "watts": 45.2, "amps": 0.42, "channel": "EB832_1"}
  ]
}
```
→ Writes to measurement `apex_power`.

**`POST /api/ingest/water-tests`:**
```json
{
  "tests": [
    {"parameter": "KH", "value": 8.4, "unit": "dkh", "time": "2026-06-20T18:00:00Z"}
  ]
}
```
→ Writes to measurement `apex_water_tests`.

### Task 2.2 — InfluxDB Write Service

`backend/app/ingest/influx.py`:

```python
class InfluxWriter:
    def __init__(self, tenant_id: str, admin_client):
        self.bucket = f"reefmind_{tenant_id}"
        self.client = admin_client  # MVP: shared admin client, scope by bucket

    def write_telemetry(self, points: list[dict]) -> None:
        """Write probe telemetry points to tenant's bucket."""
        influx_points = []
        for p in points:
            ip = Point("apex_telemetry")
            ip.tag("probe_name", p["probe_name"])
            ip.tag("probe_type", p["probe_type"])
            ip.tag("unit", p["unit"])
            ip.field("value", float(p["value"]))
            if p.get("time"):
                ip.time(p["time"])
            influx_points.append(ip)
        self.client.write_api().write(bucket=self.bucket, record=influx_points)
```

### Task 2.3 — Agent Modifications

Copy relevant collector code from the existing `scripts/` directory into `agent/`:

**`agent/collector.py`:**
- Based on `apex_unified_scraper.py` and `apex_fusion_client.py`
- Instead of `write_points(cfg, points)`, it calls `POST /api/ingest/telemetry`
- Uses `httpx` instead of `influxdb_client`
- Same 60s poll loop, same failure/backoff logic
- Reads `AGENT_API_KEY` and `REEFMIND_API_URL` from env or config file

Key behavioral change:
```python
# Instead of:
from reef_core import write_points
write_points(cfg, telemetry_points)

# Do:
import httpx
response = httpx.post(
    f"{API_URL}/api/ingest/telemetry",
    headers={"Authorization": f"Bearer {AGENT_API_KEY}"},
    json={"points": telemetry_points}
)
```

**`agent/agent_config.yaml`:**
```yaml
reefmind:
  api_url: "https://your-reefmind-instance.com"
  agent_api_key: ""  # Set via env var AGENT_API_KEY

backend:
  name: apex

backends:
  apex:
    host: "192.168.3.26"
    status_path: "/cgi-bin/status.xml"
    target_outlets:
      - MainPump
      - Skimmer
      - ...
```

**`agent/docker-compose.yml`** (user-facing):
```yaml
services:
  reefmind-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: reefmind_agent
    environment:
      - AGENT_API_KEY=${AGENT_API_KEY}
      - REEFMIND_API_URL=${REEFMIND_API_URL}
      - APEX_HOST=${APEX_HOST:-192.168.3.26}
    restart: unless-stopped
```

### Task 2.4 — Fusion Sync (Agent-Side)

**`agent/fusion_sync.py`:**
- Based on `apex_fusion_ilog_sync.py`, `apex_mlog_sync.py`, `apex_fusion_log_sync.py`
- Uses Fusion API credentials from `agent_config.yaml`
- Pushes historical data to the same ingest endpoints
- Runs on a cron schedule inside the container (same dcron pattern as current)

---

## Phase 3: Dashboard Web UI

**Goal:** The full monitoring experience — mirroring the existing `modern-reef-dashboard.json` as a React web app, with community dashboard JSON import/export.

### Task 3.0 — Analyze the Grafana Dashboard JSON

Before building, study `dashboards/modern-reef-dashboard.json` to identify all panels:

```
Panel types in the existing dashboard:
├── Time-series line charts: Temp, pH, ORP, Salt (with thresholds)
├── Status grid: Outlet ON/OFF states (colored tiles)
├── Gauge/stat: Latest Temp, Latest pH (big number cards)
├── Table: Water test history (Ca, KH, Mg, NO3, PO4)
├── Bar chart: Power consumption per outlet (watts)
└── Time-series: Power over time (total watts)
```

Each panel maps to a React component. The Grafana JSON's `targets` field (which defines data source queries) maps to the InfluxDB Flux query the component should make.

**Community dashboard import/export:**
Store dashboard configurations as JSON in PostgreSQL (a `dashboard_configs` table):
```sql
dashboard_configs:
  id              UUID PK
  tenant_id       UUID FK → tenants
  name            VARCHAR
  description     TEXT
  config_json     JSONB  -- panel definitions, layout, queries
  is_shared       BOOLEAN default false
  source          VARCHAR  -- "reefmind" | "grafana_import"
  created_at      TIMESTAMP
  updated_at      TIMESTAMP
```

The import endpoint accepts both:
- Native ReefMind JSON (same schema as `config_json`)
- Grafana JSON (strips Grafana-specific metadata, maps data source UIDs to ReefMind tenant ID, returns a preview of what was auto-detected)

### Task 3.1 — Dashboard API Endpoints

`backend/app/dashboard/`:

**`GET /api/dashboard/summary`** — returns everything the dashboard needs in one call:

```json
{
  "latest": {
    "Temp": {"value": 78.3, "unit": "F", "time": "2026-06-21T12:00:00Z"},
    "pH": {"value": 8.12, "unit": "pH", "time": "..."},
    "ORP": {"value": 380, "unit": "mV", "time": "..."},
    "Salt": {"value": 35.2, "unit": "PPT", "time": "..."}
  },
  "telemetry": {
    "Temp": [{"time": "...", "value": 78.1}, {"time": "...", "value": 78.3}],
    "pH": [...]
  },
  "outlets": [
    {"name": "MainPump", "state": 1, "state_display": "ON"},
    {"name": "Skimmer", "state": 1, "state_display": "ON"}
  ]
}
```

The telemetry arrays are pre-aggregated: for the time range `[now-24h, now]` at 5-min resolution, or `[now-7d, now]` at 30-min resolution. The web frontend selects which range to display.

Backend queries InfluxDB via Flux:
```python
query = f'''
  from(bucket: "reefmind_{tenant_id}")
    |> range(start: -24h)
    |> filter(fn: (r) => r._measurement == "apex_telemetry")
    |> filter(fn: (r) => r.probe_name == "Temp")
    |> aggregateWindow(every: 5m, fn: mean)
'''
```

**`GET /api/dashboard/telemetry/{probe_name}`** — query specific probe with custom range:
Query params: `range=24h|7d|30d`, `resolution=auto` (auto-calculated)

### Task 3.2 — React App Scaffold

```bash
cd web
npm create vite@latest . -- --template react-ts
npm install react-router-dom @tanstack/react-query tailwindcss @tailwindcss/vite echarts echarts-for-react lucide-react
```

**`src/api/client.ts`:**
- Axios instance with base URL from env
- Interceptor to attach JWT from localStorage
- Interceptor to refresh JWT on 401

**Routes:**
- `/` → redirect to `/dashboard` if logged in, else `/login`
- `/login` → Login page
- `/register` → Register page
- `/onboarding` → First-time setup wizard (1 step: configure Apex IP, probes)
- `/dashboard` → Main monitoring dashboard
- `/settings` → Edit probe list, outlets, Fusion creds
- `/csv-import` → CSV upload & mapping UI

### Task 3.3 — Dashboard Page

**Layout:** Left sidebar nav + main content area

**Components on Dashboard:**

| Component | Data Source | What It Shows |
|-----------|-------------|---------------|
| `LatestReadings` | `/api/dashboard/summary.latest` | 4 metric cards: Temp, pH, ORP, Salt with current value + trend arrow |
| `TimeSeriesChart` | `/api/dashboard/telemetry/Temp` | Line chart: Temp over 24h with time range selector (24h / 7d / 30d) |
| `TimeSeriesChart` | `/api/dashboard/telemetry/pH` | Line chart: pH over same time range |
| `OutletGrid` | `/api/dashboard/summary.outlets` | Grid of outlet cards: name + ON/OFF badge + color (green/red) |
| `NemoWidget` (floating) | Nemo API | Chat bubble in bottom-right, opens to ask questions about tank data |

**Time range selector:** Button group [24h / 7d / 30d] at top of dashboard. Changes range for all charts simultaneously.

### Task 3.4 — ECharts Wrapper

`src/components/charts/TimeSeriesChart.tsx`:

```tsx
interface Props {
  title: string
  data: { time: string; value: number }[]
  unit: string
  color: string
  yMin?: number
  yMax?: number
}

function TimeSeriesChart({ title, data, unit, color }: Props) {
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: unit },
    series: [{
      type: 'line',
      data: data.map(d => [d.time, d.value]),
      smooth: true,
      lineStyle: { color, width: 2 },
      areaStyle: { color: `${color}20`, opacity: 0.3 },
      showSymbol: false,
    }]
  }
  return <ReactECharts option={option} style={{ height: 300 }} />
}
```

### Task 3.5 — Onboarding Wizard

Step-by-step flow shown after registration:

1. **Tank name** (free text)
2. **Apex controller IP** (with instructions on how to find it)
3. **Probe selection** (checkboxes: Temp, pH, ORP, Salt — select which they have)
4. **Outlet selection** (text input for outlet names, one per line)
5. **Fusion credentials** (optional — username, password, Apex ID)
6. **Agent setup** (shows their API key + download link for docker-compose.yml)

The wizard writes to `PUT /api/tenant/config` for each step or once at the end.

---

## Phase 4: CSV Import Web Flow

**Goal:** Users upload historical CSV files via the web UI, map columns, and trigger import.

### Task 4.1 — CSV Import API

**`POST /api/csv/upload`** — multipart file upload:
- Saves file to local storage (or S3-compatible) at `data/csv_imports/{tenant_id}/{import_id}/{filename}`
- Creates `CsvImport` record with status=`pending`
- Returns `import_id`

**`GET /api/csv/imports`** — list imports for tenant

**`GET /api/csv/imports/{id}`** — get import details, including auto-detected column mapping

**`POST /api/csv/imports/{id}/preview`** — auto-detect column mapping:
- Reads first 20 rows of CSV
- Runs the column pattern matcher (ported from `apex_csv_import.py`)
- Returns suggested mapping: `{"Temp": "apex_telemetry", "pH": "apex_telemetry", "KH": "apex_water_tests"}`

**`POST /api/csv/imports/{id}/confirm`** — accepts mapping:
- Receives `{column_mapping: {...}}` — user corrections to auto-detected mapping
- Enqueues import task via ARQ
- Returns immediately with status=`processing`

**Task (worker):** `csv_import_task(import_id)`:
- Reads CSV file in chunks
- Applies column mapping
- Writes to InfluxDB tenant bucket
- Updates `rows_imported`, `rows_skipped`, status

### Task 4.2 — CSV Import Page UI

**`/csv-import` page:**

1. **Upload section** — drag-and-drop or file picker
2. **Import history table** — recent imports with status badges
3. **Column mapping screen** (shown after upload):
   - Table showing CSV column headers (left) → detected measurement + field (right)
   - Dropdown for user to correct the mapping
   - "Confirm & Import" button
4. **Progress indicator** — polls `GET /api/csv/imports/{id}` every 2s while processing, shows progress bar

---

## Phase 5: Nemo General Advisor + Deployment

### Task 5.1 — Nemo as General Reef Advisor

Nemo is a general reef-keeping knowledge assistant in MVP. No per-tank InfluxDB access.

**Architecture:**
```
┌────────────────────────────────┐
│   Nemo Chat Widget (React)     │
│   Floating bubble in dashboard │
│   ↓ type question →            │
│   POST /api/nemo/ask           │
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│  Nemo Backend (FastAPI proxy)  │
│                                │
│  1. Receive question + context │
│  2. Query knowledge base (RAG) │
│     └ Vector DB of reef2reef   │
│       articles/knowledge       │
│  3. Call AI provider with:     │
│     System: "You are a reef    │
│       tank advisor..."         │
│     + retrieved context        │
│  4. Stream response back (SSE) │
└────────────────────────────────┘
```

**Knowledge base bootstrapping:**
- Seed with a curated set of reefing knowledge (KH stability, temp ranges, nutrient cycling, etc.)
- For MVP, embed a static FAQ / knowledge document as system prompt context
- Future: RAG pipeline that ingests reef2reef.com content into a vector database (pgvector or Qdrant)

**Nemo backend is part of the FastAPI app** (not a separate service like the current standalone nemo_server.py). It's just a proxy to the AI provider with a fixed system prompt plus optional RAG context.

**API:**
```
POST /api/nemo/ask
  Body: { "question": "What temp should my SPS tank be?" }
  Response: SSE stream with AI answer
```

**System prompt (MVP):**
```
You are Nemo, a reef tank advisor. You help reef keepers with common questions
about water parameters, equipment, livestock, and troubleshooting.

Rules:
- Only answer reef-keeping questions. Politely decline unrelated topics.
- Cite general guidelines (e.g., "Most SPS tanks run at 76-78°F").
- Do NOT make up tank-specific data — you don't have access to the user's tank.
- Be concise but helpful. Suggest next steps when appropriate.
```

### Task 5.2 — Docker Compose for Production

**`docker-compose.yml`** additions:
- Nginx reverse proxy (Caddy or Nginx) in front of the API + web
- Automatic SSL via Let's Encrypt (Caddy does this natively)
- Health check endpoints

### Task 5.3 — Data Migration Script

**`scripts/migrate_data.py`**: Exports Kevin's existing InfluxDB data and imports it to the cloud.

```
Usage: python scripts/migrate_data.py \
  --source-influx http://localhost:8086 \
  --source-token <token> \
  --source-org reef \
  --source-bucket reef_telemetry \
  --target-api https://reefmind.io \
  --agent-key <key>
```

Logic:
1. Query InfluxDB for all data in `apex_telemetry`, `apex_outlet_states`, `apex_power`, `apex_water_tests`
2. Batch-write to cloud ingest API (with real timestamps preserved)
3. Prints progress and completion stats

---

## Implementation Sequence

This is the order Cody should build in. Each phase depends on the previous one.

```
Week 1
├── Phase 0: Scaffolding + DB models + Docker Compose  (Day 1-2)
├── Phase 1: Auth + tenant management                   (Day 2-3)
└── Phase 2: Ingest API + agent modifications           (Day 3-5)

Week 2
├── Phase 3: Dashboard API + Web UI                     (Day 5-8)
├── Phase 4: CSV import web flow                        (Day 8-9)
└── Phase 5: Nemo integration + deploy config           (Day 9-10)

Week 3
├── Data migration (Kevin's existing data)
├── QA + edge case fixes
└── Deploy to VPS + agent test
```

---

## Cody Handoff Checklist

Each checkbox is a file or task that Cody creates. Check off as completed.

### Phase 0 — Project Scaffolding

- [ ] `backend/requirements.txt` — all Python deps
- [ ] `backend/Dockerfile` — Python 3.13-slim build
- [ ] `backend/app/__init__.py`
- [ ] `backend/app/config.py` — pydantic-settings Settings
- [ ] `backend/app/main.py` — FastAPI app with CORS + lifespan
- [ ] `backend/app/db/__init__.py`
- [ ] `backend/app/db/base.py` — DeclarativeBase
- [ ] `backend/app/db/session.py` — async engine + get_db
- [ ] `backend/app/db/models/__init__.py`
- [ ] `backend/app/db/models/tenant.py` — Tenant model
- [ ] `backend/app/db/models/user.py` — User model
- [ ] `backend/app/db/models/tenant_config.py` — TenantConfig model
- [ ] `backend/app/db/models/csv_import.py` — CsvImport model
- [ ] `backend/app/migrations/alembic.ini`
- [ ] `backend/app/migrations/env.py`
- [ ] `backend/app/migrations/versions/001_initial.py` — auto-generated
- [ ] `backend/app/ingest/__init__.py`
- [ ] `backend/app/ingest/influx.py` — InfluxDB bootstrap + tenant bucket creation
- [ ] `backend/app/workers/__init__.py`
- [ ] `backend/app/workers/worker.py` — ARQ worker class
- [ ] `backend/tests/conftest.py`
- [ ] `docker-compose.yml` — cloud stack (postgres, influxdb, redis, api, web, worker)
- [ ] `.env.example` — all required env vars with comments

### Phase 1 — Auth & Tenant Management

- [ ] `backend/app/auth/__init__.py`
- [ ] `backend/app/auth/jwt.py` — JWT creation/verification
- [ ] `backend/app/auth/password.py` — bcrypt hash/verify
- [ ] `backend/app/auth/dependencies.py` — get_current_user, verify_agent_api_key
- [ ] `backend/app/auth/router.py` — register, login, refresh endpoints
- [ ] `backend/app/tenants/__init__.py`
- [ ] `backend/app/tenants/service.py` — Tenant CRUD, API key generation
- [ ] `backend/app/tenants/router.py` — GET/PUT config, regenerate agent key
- [ ] `backend/tests/test_auth.py` — register + login tests

### Phase 2 — Ingest API & Agent

- [ ] `backend/app/ingest/router.py` — 4 ingest endpoints (telemetry, outlets, power, water-tests)
- [ ] `backend/app/ingest/service.py` — write orchestration
- [ ] `backend/app/ingest/influx.py` — update with write methods
- [ ] `backend/tests/test_ingest.py`
- [ ] `agent/Dockerfile` — Python agent image
- [ ] `agent/docker-compose.yml` — user-facing agent deploy
- [ ] `agent/collector.py` — modified apex_unified_scraper (httpx POST instead of influxdb_client)
- [ ] `agent/fusion_sync.py` — modified fusion sync scripts
- [ ] `agent/agent_shared.py` — agent-side shared helpers (config, HTTP client)
- [ ] `agent/agent_config.yaml` — agent-side config template

### Phase 3 — Dashboard

- [ ] `backend/app/db/models/dashboard_config.py` — DashboardConfig model (name, config_json, is_shared, source)
- [ ] `backend/app/dashboard/__init__.py`
- [ ] `backend/app/dashboard/service.py` — Flux queries for summary + telemetry
- [ ] `backend/app/dashboard/router.py` — GET /api/dashboard/summary, GET telemetry/{probe}, POST /import-grafana-json
- [ ] `backend/app/dashboard/grafana_importer.py` — Parse Grafana JSON → ReefMind panel config
- [ ] `backend/tests/test_dashboard.py`
- [ ] `web/` — Vite + React + Tailwind scaffold
- [ ] `web/src/api/client.ts` — Axios instance + JWT interceptor
- [ ] `web/src/api/dashboard.ts` — fetch functions
- [ ] `web/src/pages/Login.tsx`
- [ ] `web/src/pages/Register.tsx`
- [ ] `web/src/pages/Dashboard.tsx` — Main dashboard with all panels from modern-reef-dashboard.json
- [ ] `web/src/pages/Settings.tsx`
- [ ] `web/src/pages/Onboarding.tsx`
- [ ] `web/src/components/Layout.tsx` — sidebar + header
- [ ] `web/src/components/ProtectedRoute.tsx`
- [ ] `web/src/components/charts/TimeSeriesChart.tsx` — ECharts wrapper (Temp, pH, ORP, Salt)
- [ ] `web/src/components/charts/LatestReadings.tsx` — metric cards (big number cards)
- [ ] `web/src/components/charts/OutletGrid.tsx` — ON/OFF color grid
- [ ] `web/src/components/charts/WaterTestTable.tsx` — Ca/KH/Mg history table
- [ ] `web/src/components/charts/PowerBarChart.tsx` — Power per outlet (watts)
- [ ] `web/src/components/charts/PowerTimeSeries.tsx` — Total power over time
- [ ] `web/src/components/DashboardImportExport.tsx` — Import/export dashboard JSON (Grafana-compatible)
- [ ] `web/src/components/NemoWidget.tsx` — chat widget (general reef advisor)
- [ ] `web/Dockerfile` — Nginx static build
- [ ] `web/nginx.conf` — SPA routing

### Phase 4 — CSV Import

- [ ] `backend/app/csv_import/__init__.py`
- [ ] `backend/app/csv_import/service.py` — column mapping, file management
- [ ] `backend/app/csv_import/column_mapper.py` — ported pattern matchers from apex_csv_import.py
- [ ] `backend/app/csv_import/router.py` — upload, preview, confirm, list endpoints
- [ ] `backend/app/workers/tasks.py` — csv_import_task ARQ task
- [ ] `backend/tests/test_csv_import.py`
- [ ] `web/src/api/csv.ts` — upload + import fetch functions
- [ ] `web/src/pages/CsvImport.tsx`
- [ ] `web/src/components/CsvMappingPreview.tsx`

### Phase 5 — Nemo General Advisor + Deployment

- [ ] `backend/app/nemo/__init__.py` — Nemo router (POST /api/nemo/ask)
- [ ] `backend/app/nemo/service.py` — AI provider call with SSE streaming + system prompt
- [ ] `backend/app/nemo/knowledge_base.py` — Static reefing knowledge / FAQ context
- [ ] `scripts/migrate_data.py` — local InfluxDB → cloud ingest migration
- [ ] `scripts/seed_tenant.py` — create Kevin's tenant + config
- [ ] `Caddyfile` — production reverse proxy with auto SSL (used on VPS)
- [ ] Updated `docker-compose.yml` — add Caddy reverse proxy profile (disabled for local dev)
- [ ] CI/CD notes or script for VPS deploy

---

## Key Metrics for Launch Decision (when is MVP "done")

| Milestone | Criterion |
|-----------|-----------|
| **Alpha** | Kevin can register, configure his Apex, see live data on dashboard |
| **Beta (closed)** | 1-2 friends can sign up, configure their Apex, see data |
| **Beta (open)** | CSV import works, Fusion sync works, Nemo works per-tenant |
| **Launch** | Billing is optional (free tier exists), alerts work, no known data loss bugs |

---

## Future-Looking Notes (Post-MVP)

These are NOT for Cody to build now — just awareness:

- **Billing/Stripe**: Add a `subscriptions` table tied to Tenant. Free tier = 7-day data retention, 1 user. Paid tier = unlimited retention, 5 users.
- **Alert rules**: Store in DB. Background worker evaluates rules against latest InfluxDB data. Triggers email/push notification.
- **Public landing page**: Marketing site separate from the app.
- **Mobile app**: React Native or PWA from the existing React codebase.
- **Anomaly detection**: ML model trained on tenant's historical data, flags unusual readings via Nemo.
- **Multi-controller support**: The backend abstraction already exists — just add `profilux/`, `hydros/` backends.
- **WebSockets / Server-Sent Events**: Replace polling with live push for dashboard updates.
