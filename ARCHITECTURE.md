# ReefMind — Architecture Reference

## Stack Overview

The ReefMind Cloud SaaS is a containerized application designed for multi-tenancy, providing live monitoring, AI-driven tank advice, and data management for reef controllers.

```
docker-compose.yml
│
├── postgres:16-alpine  — Relational DB for users, tenants, config
├── influxdb:2.7-alpine — Time-series DB for telemetry
├── redis:7-alpine      — Caching (Nemo AI context)
├── api (FastAPI)       — SaaS backend, background Fusion collector
└── web (React + Vite)  — Dashboard SPA
```

## Services

### API (FastAPI)
- **Container**: `api`
- **Function**: Handles authentication (JWT), tenant configuration, data ingestion, and the Nemo AI assistant.
- **Background Tasks**:
  - **Fusion Collector**: Runs in an `asyncio.create_task` during the application lifespan. It queries the Fusion API every 300s (5min) for all tenants with credentials, writing readings to InfluxDB.
  - **CSV Processing**: Synchronous parsing of CSV imports with preview functionality.

### Ingest (No Agent Container)
- **Design**: The collection logic runs server-side within the API container.
- **Why**: Eliminates the need for users to deploy and manage a separate local agent container.
- **Data Collection**: `api/app/services/collector.py` coordinates with `fusion_live.py` to poll Fusion Cloud for all configured tenants.

### Nemo AI
- **Features**: Tank-specific context awareness, outlet/probe data injection, and support for multiple LLM providers (OpenAI, Anthropic, Gemini, DeepSeek).
- **Endpoint**: `POST /api/nemo/ask`. Uses a 60s in-memory cache for recent Fusion data.

## Deployment

```bash
docker compose up -d
```

## Data Flow

```
Fusion Cloud API
    │
    ├── FusionLiveClient ──► api (5-min loop) ──► InfluxDB
                                                     │
                                             ┌───────┴──────┐
                                             │      web     │
                                             │     nemo     │
                                             └──────────────┘
```

## File Layout

```
ReefMind-Cloud/
├── docker-compose.yml
├── api/
│   ├── app/
│   │   ├── models/       # SQLAlchemy models (tenant.py, user.py, etc.)
│   │   ├── routers/      # API routes (auth.py, ingest.py, nemo.py, fusion.py, etc.)
│   │   ├── services/     # Business logic (auth.py, collector.py, influx.py, etc.)
│   │   ├── schemas/      # Pydantic models (auth.py, ingest.py, telemetry.py)
│   │   └── middleware/   # Authentication middleware
├── web/                  # React + Vite + ECharts
└── docs/                 # Project documentation
```

## Historical Context

- **[v0.1.0]**: Initial SaaS release. Shifted from on-prem agent design to server-side Fusion collection. Introduced per-tenant InfluxDB bucketing.
