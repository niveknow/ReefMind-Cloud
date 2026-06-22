# Smoke Test Suite — ReefMind Cloud v0.1.0

## Purpose

Quick validation that the application is basically alive and testable. Run these first before any UAT or regression cycle.

## Prerequisites

- `docker compose up -d` has been run
- All 5 containers are healthy (postgres, influxdb, redis, api, web)
- Ports 8000 (API) and 8080 (Web) are accessible

---

### SMOKE-001 — API health check

- **Step:** `curl -s http://localhost:8000/api/health`
- **Expected:** HTTP 200, JSON with `status: "ok"`, `service: "reefmind-api"`, `version: "0.1.0"`
- **Status:** [PENDING]

### SMOKE-002 — Web app loads

- **Step:** Navigate to `http://localhost:8080/`
- **Expected:** HTML page loads, React app renders (login page visible)
- **Status:** [PENDING]

### SMOKE-003 — API via Nginx proxy

- **Step:** `curl -s http://localhost:8080/api/health`
- **Expected:** HTTP 200, health JSON returned
- **Status:** [PENDING]

### SMOKE-004 — Registration works

- **Step:** `curl -s -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d '{"email":"smoke-test@test.reef","password":"Test1234!","display_name":"Smoke Test","tenant_name":"Smoke Tenant"}'`
- **Expected:** HTTP 200, response contains `access_token`, `tenant_id`, `user_id`
- **Status:** [PENDING]

### SMOKE-005 — Login works with registered user

- **Step:** `curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"smoke-test@test.reef","password":"Test1234!"}'`
- **Expected:** HTTP 200, response contains `access_token`
- **Status:** [PENDING]

### SMOKE-006 — Authenticated tenant config accessible

- **Step:** Login first, then `curl -s http://localhost:8000/api/tenant/config -H "Authorization: Bearer $TOKEN"`
- **Expected:** HTTP 200, config object returned with `backend_type`, `agent_api_key`, etc.
- **Status:** [PENDING]

### SMOKE-007 — Ingest endpoint exists and requires API key

- **Step:** `curl -s -X POST http://localhost:8000/api/ingest/telemetry -H "Content-Type: application/json" -d '{"readings":[]}'`
- **Expected:** HTTP 401 or 403 (not 404, not 500)
- **Status:** [PENDING]

### SMOKE-008 — Web app login form accessible

- **Step:** Load `http://localhost:8080/login` in browser
- **Expected:** Login form renders with email and password fields, submit button
- **Status:** [PENDING]

### SMOKE-009 — No console errors on login page

- **Step:** Load `http://localhost:8080/login` and check browser console
- **Expected:** No critical JS errors or 404s for assets
- **Status:** [PENDING]

### SMOKE-010 — Dashboard redirects to login when unauthenticated

- **Step:** Navigate browser to `http://localhost:8080/dashboard` without logging in
- **Expected:** Redirected to `/login`
- **Status:** [PENDING]

---

## Smoke Test Results

| # | Test | Result | Notes |
|---|------|--------|-------|
| SMOKE-001 | API health | [PENDING] | |
| SMOKE-002 | Web loads | [PENDING] | |
| SMOKE-003 | Nginx proxy | [PENDING] | |
| SMOKE-004 | Registration | [PENDING] | |
| SMOKE-005 | Login | [PENDING] | |
| SMOKE-006 | Tenant config | [PENDING] | |
| SMOKE-007 | Ingest endpoint | [PENDING] | |
| SMOKE-008 | Login form | [PENDING] | |
| SMOKE-009 | Console errors | [PENDING] | |
| SMOKE-010 | Auth redirect | [PENDING] | |
| **Total** | | **0/10 PASS** | |
