# Regression Test Suite — ReefMind Cloud v0.1.0

## Purpose

Ensure that new fixes do not break previously passing behavior. Run after any Cody fix deployment.

## Core Regression (always run)

### REG-001 — Auth and session

- **Tests:** TEST-002, TEST-004, TEST-007
- **Why:** Registration and login are the gateway to every feature. If auth breaks, nothing works.
- **Scope:** Registration creates tenant+config. Login returns valid JWT. Protected routes reject unauthenticated.

### REG-002 — Auth mode separation

- **Tests:** TEST-008
- **Why:** Must ensure JWT cannot be used for ingest and API key cannot be used for dashboard.
- **Scope:** Ingest endpoints accept only API key, not JWT.

### REG-003 — Tenant data isolation

- **Tests:** TEST-027
- **Why:** The most critical security invariant. If isolation breaks, all tenants' data is exposed.
- **Scope:** Tenant A cannot see Tenant B's telemetry data. Each tenant only sees their own.

### REG-004 — Data ingestion pipeline

- **Tests:** TEST-009, TEST-012
- **Why:** If ingest breaks, no new data enters the system. If telemetry query breaks, users see nothing.
- **Scope:** Ingest telemetry → query telemetry summary → verify data round-trips.

### REG-005 — Background collector

- **Tests:** TEST-036, TEST-037
- **Why:** The collector is the primary data pipeline. If it fails, no Fusion data is collected.
- **Scope:** Collector polls Fusion, writes to InfluxDB. Handles missing config gracefully.

### REG-006 — Fusion API endpoints

- **Tests:** TEST-040 (save), TEST-019 (validate), TEST-021 (status)
- **Why:** Fusion integration is the core value proposition. Discovery, save, and status must work.
- **Scope:** Full Fusion flow: configure → discover → save → verify persistence.

### REG-007 — Tenant config persistence

- **Tests:** TEST-015, TEST-016, TEST-017, TEST-018
- **Why:** User settings (Fusion creds, Nemo key, agent key) must persist and respect updates.
- **Scope:** Update config → read back — verify changes persist. Regenerate API key — old key invalidated.

---

## Adjacent Regression (run when fixes affect related areas)

### REG-008 — Nemo AI (run after auth or config changes)

- **Tests:** TEST-021, TEST-022, TEST-042
- **Why:** Nemo depends on tenant config for API keys and Fusion credentials. Config changes could break it.
- **Scope:** Status reflects config. General questions answered. No-key case returns offline message.

### REG-009 — CSV import (run after ingest or DB changes)

- **Tests:** TEST-025, TEST-026
- **Why:** CSV upload depends on DB persistence and file handling. Ingest changes could break it.
- **Scope:** Upload returns preview. Import list shows history.

### REG-010 — Web UI (run after API changes)

- **Tests:** TEST-032, TEST-034, TEST-031
- **Why:** Frontend depends on API contract. API changes may break the UI.
- **Scope:** Login form works. Dashboard loads. Auth redirect works.

---

## Regression Run Log

| Run ID | Date | Scope | Tests Run | Pass | Fail | Notes |
|--------|------|-------|-----------|------|------|-------|
| | | | | | | |
