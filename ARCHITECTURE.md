# ReefMind — Architecture Reference

## Stack Overview

```
docker-compose.yml  (single deploy: `docker compose up -d`)
│
├── influxdb     — Time-series DB (port 8086)
├── grafana      — Dashboard UI (port 3030)
├── nemo         — AI tank assistant (port 8766)
├── collector    — Live controller poller (daemon)
└── cron         — Fusion API sync jobs (dcron)
```

## Services

### collector (daemon)
- **Container**: `reef_collector`
- **Code**: `scripts/apex_unified_scraper.py`
- **What it does**: Polls Apex controller at your configured IP every 60s. Writes live probe/power/outlet/status data to InfluxDB.
- **Resilience**: 5s poll on failure, 60s on success. Records `error_detail` on failures.
- **Config**: `reef_config.yaml` (env var overrides)
- **Dockerfile**: `scripts/Dockerfile.collector`

### cron (batch scheduler)
- **Container**: `reef_cron`
- **Base**: `python:3.13-slim` + dcron
- **What it does**: Runs three Fusion API sync scripts on schedule.

| Script | Schedule | Purpose |
|--------|----------|---------|
| `apex_fusion_ilog_sync.py` | Sun 5AM | Backfill historical probe data (10-min res, 180d) |
| `apex_mlog_sync.py` | Every 6h | Sync water test results (KH/Ca/Mg) |
| `apex_fusion_log_sync.py` | Every 6h | Sync tank notes/observations |

- **Dockerfile**: `scripts/Dockerfile.cron`

## Credential Sources

All credentials are passed as environment variables via docker-compose.yml, sourced from `.env`. No credentials are baked into Docker images.

| Env Var | Source | Required By |
|---------|--------|-------------|
| `INFLUX_TOKEN` | `.env` | collector, cron, nemo |
| `INFLUX_ORG` | `.env` (default: `my_reef`) | collector, cron, nemo |
| `INFLUX_BUCKET` | `.env` (default: `reef_telemetry`) | collector, cron, nemo |
| `APEX_HOST` | `.env` | collector (your Neptune controller IP) |
| `FUSION_USER` | `.env` | cron |
| `FUSION_PASS` | `.env` | cron |
| `APEX_FUSION_ID` | `.env` | cron |
| `GRAFANA_USER` | `.env` (default: `admin`) | grafana |
| `GRAFANA_PASSWORD` | `.env` | grafana |
| `AI_API_KEY` | `.env` | nemo (set `AI_PROVIDER` to match) |

## File Layout

```
ReefMind/
├── docker-compose.yml
├── .env                    # All credentials (one file)
├── .env.example            # Template — copy to .env
├── reef_config.yaml         # Platform configuration (controller, InfluxDB, power channels)
├── apex-config.yaml          # DEPRECATED — kept for backward compatibility
├── scripts/
│   ├── Dockerfile.collector
│   ├── Dockerfile.cron
│   ├── Dockerfile.backup
│   ├── reef_core.py        # Shared library (config, InfluxDB, retry)
│   ├── apex_shared.py      # Deprecated shim → reef_core.py
│   ├── apex_unified_scraper.py
│   ├── apex_fusion_ilog_sync.py
│   ├── apex_mlog_sync.py
│   ├── apex_fusion_log_sync.py
│   └── apex_fusion_client.py
├── backends/
│   ├── base.py             # CollectorBackend interface
│   └── apex/               # Neptune Apex implementation
└── dashboards/
    └── modern-reef-dashboard.json
```

> **Note:** Script names with `apex_` prefix are Neptune Apex controller-specific tools. `reef_core.py` is the framework-agnostic shared library.

## Deployment

### First time
```bash
cp .env.example .env    # edit .env with your credentials
docker compose up -d
```

### Rebuild a single service (after code changes)
```bash
docker compose build --no-cache <service>
docker compose up -d --no-deps --force-recreate <service>
```

### Common rebuilds
```bash
# Collector after changing poll logic
docker compose build --no-cache collector && docker compose up -d --no-deps --force-recreate collector

# Cron after changing sync schedules or scripts
docker compose build --no-cache cron && docker compose up -d --no-deps --force-recreate cron
```

> **⚠️ Both `--no-cache` and `--force-recreate` are required on TrueNAS NFS-backed datasets** — Docker's COPY layer may not detect file changes without `--no-cache`. On standard filesystems (ext4, ZFS, etc.), you can omit `--no-cache` for faster rebuilds. `--force-recreate` is always needed with `--no-deps` since Docker won't restart a running container otherwise.

## Data Flow

```
Apex Controller (your controller IP)
    │
    ├── status.xml ──────► collector (60s loop) ────► InfluxDB
    │                                                    │
Fusion Cloud API                                          │
    │                                                     │
    ├── ilog ──► cron (Sun 5AM, 10-min res) ─────────────┤
    ├── mlog ──► cron (every 6h, water tests) ───────────┤
    └── log  ──► cron (every 6h, tank notes) ────────────┤
                                                         │
                                                    ┌────┴────┐
                                                    │ grafana │
                                                    │  nemo   │
                                                    └─────────┘
```

## Historical Context

- **Pre-2026**: Collector ran as Hermes cron job. Fusion syncs also Hermes cron.
- **2026-06-16**: [v0.12.0] Collector containerized as Docker daemon. Added resilience (5s/60s poll, error_detail capture, recovery logging). Fusion syncs moved to dedicated cron container.
- **2026-06-17**: [v0.15.0] Rebranded from "Apex Dashboard" to ReefMind. Container names changed from `apex_*` to `reef_*`. Added multi-controller backend support.