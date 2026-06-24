# UAT Sprint Plan — ReefMind Cloud

## Project

ReefMind-Cloud — Multi-tenant SaaS platform for Neptune Apex aquarium controllers.

## Build Under Test

v0.1.0 — Initial Build (commit b541f3e)

## Source Requirements

- **Product requirements:** `docs/saas-architecture-review.md` — Full architecture design by Archie
- **MVP scope:** `docs/saas-implementation-plan.md` — Phase 0 + Phase 1 features
- **API spec:** `api/app/routers/` — 7 routers (auth, ingest, telemetry, tenant_config, fusion, nemo, csv_import)
- **Auth and permissions:** JWT (Bearer) + API key (X-API-Key), tenant-scoped data isolation
- **Data model:** `api/app/models/` — User, Tenant, TenantConfig, CsvImport

## Test Cases

---

### TEST-001 — Health endpoint responds

- **Requirement reference:** ARCHITECTURE.md — API service health
- **User role:** Unauthenticated
- **Preconditions:** API container running on port 8000
- **Steps:**
  1. Send `GET /api/health`
- **Expected result:** Returns `{"status": "ok", "service": "reefmind-api", "version": "0.1.3"}` with HTTP 200
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Smoke test — must pass before any other testing

---

### TEST-002 — User registration creates tenant + config

- **Requirement reference:** `api/app/routers/auth.py` — `/api/auth/register`
- **User role:** Unauthenticated
- **Preconditions:** API + Postgres running, email not already registered
- **Steps:**
  1. Send `POST /api/auth/register` with valid email, password, display_name, tenant_name
  2. Verify response contains `access_token`, `tenant_id`, `user_id`
  3. Decode JWT to verify it contains `user_id`, `tenant_id`, `email`
- **Expected result:** HTTP 201/200. User, Tenant, and TenantConfig created in DB. InfluxDB bucket created. JWT returned.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Test with known-clean state first

---

### TEST-003 — Duplicate email registration rejected

- **Requirement reference:** `api/app/routers/auth.py` line 18-19
- **User role:** Unauthenticated
- **Preconditions:** Email already registered from TEST-002
- **Steps:**
  1. Send `POST /api/auth/register` with same email as TEST-002
- **Expected result:** HTTP 409 with `{"detail": "Email already registered"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Negative path

---

### TEST-004 — Login with valid credentials

- **Requirement reference:** `api/app/routers/auth.py` — `/api/auth/login`
- **User role:** Registered user
- **Preconditions:** User exists from TEST-002
- **Steps:**
  1. Send `POST /api/auth/login` with registered email and correct password
  2. Verify response contains `access_token`, `tenant_id`, `user_id`
- **Expected result:** HTTP 200. Valid JWT returned.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-005 — Login with invalid password

- **Requirement reference:** `api/app/routers/auth.py` lines 70-74
- **User role:** Registered user
- **Preconditions:** User exists from TEST-002
- **Steps:**
  1. Send `POST /api/auth/login` with correct email and wrong password
- **Expected result:** HTTP 401 with `{"detail": "Invalid email or password"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Negative path

---

### TEST-006 — Login with non-existent email

- **Requirement reference:** `api/app/routers/auth.py`
- **User role:** Unauthenticated
- **Preconditions:** None
- **Steps:**
  1. Send `POST /api/auth/login` with unregistered email
- **Expected result:** HTTP 401 with `{"detail": "Invalid email or password"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Negative path — should not reveal whether email exists

---

### TEST-007 — Protected API rejects unauthenticated requests

- **Requirement reference:** `api/app/middleware/auth.py`
- **User role:** Unauthenticated
- **Preconditions:** API running
- **Steps:**
  1. Send `GET /api/telemetry/summary` without Authorization header
  2. Send `GET /api/tenant/config` without Authorization header
  3. Send `POST /api/fusion/discover` without Authorization header
- **Expected result:** All return HTTP 401 with `{"detail": "Not authenticated"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Auth enforcement — critical

---

### TEST-008 — Ingest endpoints require API key auth (not JWT)

- **Requirement reference:** `api/app/routers/ingest.py` lines 15-16
- **User role:** JWT-authenticated user
- **Preconditions:** Valid JWT from TEST-004
- **Steps:**
  1. Send `POST /api/ingest/telemetry` with valid JWT Bearer token (no X-API-Key)
- **Expected result:** HTTP 403 with `{"detail": "Agent API key required"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Auth mode separation — JWT should not work for ingest

---

### TEST-009 — Ingest telemetry with valid API key

- **Requirement reference:** `api/app/routers/ingest.py` — `POST /api/ingest/telemetry`
- **User role:** Agent (API key)
- **Preconditions:** Registered user with tenant config that has agent_api_key
- **Steps:**
  1. Send `POST /api/ingest/telemetry` with `X-API-Key` header and valid TelemetryBatch payload
  2. Payload: `{"readings": [{"probe_name": "Temperature", "probe_type": "Temp", "value": 78.5, "unit": "°F", "did": "base_Temp"}]}`
- **Expected result:** HTTP 200 with `{"status": "ok", "writes": 1}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires InfluxDB running

---

### TEST-010 — Ingest outlets with valid API key

- **Requirement reference:** `api/app/routers/ingest.py` — `POST /api/ingest/outlets`
- **User role:** Agent (API key)
- **Preconditions:** TEST-010 prerequisites met
- **Steps:**
  1. Send `POST /api/ingest/outlets` with `X-API-Key` header and valid OutletBatch
  2. Payload: `{"outlets": [{"outlet_name": "ReturnPump", "state": 1, "state_display": "ON"}]}`
- **Expected result:** HTTP 200 with `{"status": "ok", "writes": 1}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-011 — Ingest power with valid API key

- **Requirement reference:** `api/app/routers/ingest.py` — `POST /api/ingest/power`
- **User role:** Agent (API key)
- **Preconditions:** TEST-010 prerequisites met
- **Steps:**
  1. Send `POST /api/ingest/power` with `X-API-Key` header and valid PowerBatch
  2. Payload: `{"readings": [{"outlet_name": "ReturnPump", "watts": 45.2, "amps": 0.38, "channel": "main"}]}`
- **Expected result:** HTTP 200 with `{"status": "ok", "writes": 1}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-012 — Telemetry summary returns ingested data

- **Requirement reference:** `api/app/routers/telemetry.py` — `GET /api/telemetry/summary`
- **User role:** Authenticated (JWT)
- **Preconditions:** Data ingested via TEST-010, same tenant as user
- **Steps:**
  1. Get valid JWT via login
  2. Send `GET /api/telemetry/summary` with Bearer token
- **Expected result:** HTTP 200 with `{"readings": [...]}` containing the ingested Temperature reading
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-013 — Telemetry outlet states return correct data

- **Requirement reference:** `api/app/routers/telemetry.py` — `GET /api/telemetry/outlets`
- **User role:** Authenticated (JWT)
- **Preconditions:** Outlet data ingested via TEST-011
- **Steps:**
  1. Get valid JWT
  2. Send `GET /api/telemetry/outlets`
- **Expected result:** HTTP 200 with `{"outlets": [...], "source": "agent"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-014 — Probe history returns time-series data

- **Requirement reference:** `api/app/routers/telemetry.py` — `GET /api/telemetry/{probe_name}`
- **User role:** Authenticated (JWT)
- **Preconditions:** Probe data ingested
- **Steps:**
  1. Send `GET /api/telemetry/Temperature?duration=24h`
- **Expected result:** HTTP 200 with `{"probe": "Temperature", "data": [...]}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-015 — Tenant config retrieval (JWT required)

- **Requirement reference:** `api/app/routers/tenant_config.py`
- **User role:** Authenticated (JWT)
- **Preconditions:** User is registered and logged in
- **Steps:**
  1. Send `GET /api/tenant/config` with valid JWT
- **Expected result:** HTTP 200 with config object containing backend_type, fusion_config_configured, nemo_configured, etc. Secrets (fusion_pass) excluded.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-016 — Update tenant config (Fusion credentials)

- **Requirement reference:** `api/app/routers/tenant_config.py` — `PUT /api/tenant/config`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `PUT /api/tenant/config` with `{"fusion_user": "test@example.com", "fusion_pass": "password123", "fusion_apex_id": "test123"}`
- **Expected result:** HTTP 200 with `{"status": "ok"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-017 — Update Nemo AI config

- **Requirement reference:** `api/app/routers/tenant_config.py` lines 67-73
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `PUT /api/tenant/config` with `{"nemo_api_key": "sk-test-key", "nemo_provider": "openai", "nemo_model": "gpt-4o-mini"}`
  2. Send `GET /api/tenant/config` to verify `nemo_configured: true`
- **Expected result:** HTTP 200. Config persisted and reflects changes on read.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-018 — Regenerate agent API key

- **Requirement reference:** `api/app/routers/tenant_config.py` — `POST /api/tenant/regenerate-agent-key`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, existing agent API key
- **Steps:**
  1. Note current agent API key from config
  2. Send `POST /api/tenant/regenerate-agent-key`
  3. Send `GET /api/tenant/config` to verify new key differs
- **Expected result:** HTTP 200 with new `agent_api_key`. Old key no longer accepted for ingest.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-019 — Fusion discovery endpoint rejects empty creds

- **Requirement reference:** `api/app/routers/fusion.py` line 51-52
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `POST /api/fusion/discover` with empty fusion_username
- **Expected result:** HTTP 400 with `{"detail": "Fusion username and password are required"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Validation test

---

### TEST-020 — Fusion discovery with invalid creds returns 401

- **Requirement reference:** `api/app/routers/fusion.py` lines 54-63
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `POST /api/fusion/discover` with `{"fusion_username": "bad@user.com", "fusion_password": "wrongpass"}`
- **Expected result:** HTTP 401 with Fusion-specific error message
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** External dependency test — requires internet access to Fusion API

---

### TEST-021 — Nemo AI status returns configured state

- **Requirement reference:** `api/app/routers/nemo.py` — `GET /api/nemo/status`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `GET /api/nemo/status`
- **Expected result:** HTTP 200 with `{"configured": bool, "provider": "...", "model": "...", "source": "tenant|env|none"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-022 — Nemo AI answers general question without tank data

- **Requirement reference:** `api/app/routers/nemo.py` — `POST /api/nemo/ask`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, Nemo AI configured with valid API key
- **Steps:**
  1. Send `POST /api/nemo/ask` with `{"question": "What temperature should a reef tank be?"}`
- **Expected result:** HTTP 200 with `{"answer": "...", "model": "..."}`. Answer should be relevant reef-keeping advice.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** General question should not trigger tank data injection

---

### TEST-023 — Nemo AI injects tank context for tank-specific question

- **Requirement reference:** `api/app/routers/nemo.py` — relevance detection + _build_live_context
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, Nemo API key configured, Fusion credentials configured
- **Steps:**
  1. Send `POST /api/nemo/ask` with `{"question": "How is my tank doing?"}`
- **Expected result:** HTTP 200. Answer should reference specific tank data if Fusion credentials are valid
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** End-to-end — requires valid Fusion creds

---

### TEST-024 — Nemo AI handles empty question

- **Requirement reference:** `api/app/routers/nemo.py` line 230-231
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT
- **Steps:**
  1. Send `POST /api/nemo/ask` with `{"question": ""}`
- **Expected result:** HTTP 400 with `{"detail": "Question cannot be empty"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Input validation

---

### TEST-025 — CSV upload with valid file returns preview

- **Requirement reference:** `api/app/routers/csv_import.py` — `POST /api/csv/upload`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, CSV file with headers available
- **Steps:**
  1. Create CSV file: `Date,Temperature,pH,Salinity\n2024-01-01,78.5,8.2,35.0\n2024-01-02,78.2,8.1,35.1`
  2. Send `POST /api/csv/upload` as multipart form with file
- **Expected result:** HTTP 200 with `import_id`, `filename`, `headers`, `preview_rows`, `status: "pending"`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-026 — CSV imports list returns history

- **Requirement reference:** `api/app/routers/csv_import.py` — `GET /api/csv/imports`
- **User role:** Authenticated (JWT)
- **Preconditions:** At least one CSV uploaded via TEST-025
- **Steps:**
  1. Send `GET /api/csv/imports`
- **Expected result:** HTTP 200 with `{"imports": [...]}` containing previously uploaded files, ordered by most recent
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-027 — Tenant data isolation (cross-tenant access denied)

- **Requirement reference:** Middleware auth + telemetry router tenant_id scoping
- **User role:** Authenticated (JWT)
- **Preconditions:** Two tenants (A and B) with data ingested
- **Steps:**
  1. Log in as Tenant A user, get JWT_A
  2. Log in as Tenant B user, get JWT_B
  3. Send `GET /api/telemetry/summary` with JWT_B — note returned data
  4. Attempt to access Tenant B's data using JWT_A
- **Expected result:** Each tenant sees only their own data. Cross-tenant access returns empty data or 403/404.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** S1-CRITICAL if isolation fails

---

### TEST-028 — Register endpoint validates required fields

- **Requirement reference:** `api/app/schemas/auth.py` — RegisterRequest
- **User role:** Unauthenticated
- **Preconditions:** API running
- **Steps:**
  1. Send `POST /api/auth/register` with empty email
  2. Send `POST /api/auth/register` with empty password
  3. Send `POST /api/auth/register` with missing body
- **Expected result:** HTTP 422 with validation error details
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Input validation

---

### TEST-029 — Login endpoint validates required fields

- **Requirement reference:** `api/app/schemas/auth.py` — LoginRequest
- **User role:** Unauthenticated
- **Preconditions:** API running
- **Steps:**
  1. Send `POST /api/auth/login` with empty email
  2. Send `POST /api/auth/login` with empty password
  3. Send `POST /api/auth/login` with missing body
- **Expected result:** HTTP 422 with validation error details
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-030 — Ingest telemetry rejects invalid payload

- **Requirement reference:** `api/app/schemas/ingest.py` — TelemetryBatch
- **User role:** Agent (API key)
- **Preconditions:** Valid API key
- **Steps:**
  1. Send `POST /api/ingest/telemetry` with empty readings array
  2. Send `POST /api/ingest/telemetry` with missing probe_name
  3. Send `POST /api/ingest/telemetry` with non-numeric value
- **Expected result:** HTTP 422 with validation error
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Schema validation

---

### TEST-031 — Protected routes redirect to login in web app

- **Requirement reference:** `web/src/App.tsx` — ProtectedRoute component
- **User role:** Unauthenticated
- **Preconditions:** Web app running on port 8080
- **Steps:**
  1. Navigate browser to `http://localhost:8080/dashboard` without logging in
  2. Navigate to `http://localhost:8080/settings`
  3. Navigate to `http://localhost:8080/csv-import`
- **Expected result:** All redirect to `/login`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser-based testing

---

### TEST-032 — Web app login form submits correctly

- **Requirement reference:** `web/src/pages/LoginPage.tsx`
- **User role:** Unauthenticated
- **Preconditions:** Web app running, test user registered
- **Steps:**
  1. Navigate to `http://localhost:8080/login`
  2. Enter valid email and password
  3. Submit form
- **Expected result:** Redirect to `/dashboard`. JWT token present in localStorage.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-033 — Web app register flow creates account

- **Requirement reference:** `web/src/pages/RegisterPage.tsx`
- **User role:** Unauthenticated
- **Preconditions:** Web app running
- **Steps:**
  1. Navigate to `http://localhost:8080/register`
  2. Enter email, password, display name, tenant name
  3. Submit form
- **Expected result:** Redirect to `/dashboard`. New user created in DB.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-034 — Dashboard page loads with probe cards

- **Requirement reference:** `web/src/pages/DashboardPage.tsx`
- **User role:** Authenticated
- **Preconditions:** Web app running, user logged in with JWT
- **Steps:**
  1. Login via web UI
  2. Navigate to `/dashboard`
- **Expected result:** Dashboard renders with sidebar navigation, probe cards section, time-series chart area, outlet state grid, and Nemo chat widget (floating)
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-035 — Settings page loads Fusion config section

- **Requirement reference:** `web/src/pages/SettingsPage.tsx`
- **User role:** Authenticated
- **Preconditions:** User logged in
- **Steps:**
  1. Login via web UI
  2. Navigate to `/settings`
- **Expected result:** Settings page shows Fusion config (discover/save), Nemo AI API key configuration, and agent key regeneration section
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-036 — Fusion data collected by background collector

- **Requirement reference:** `api/app/services/collector.py` — `collector_loop()`
- **User role:** System (background task)
- **Preconditions:** Tenant has Fusion credentials configured, API has been running for >5 minutes
- **Steps:**
  1. Configure tenant with valid Fusion credentials via Settings UI or API
  2. Wait up to 5 minutes for collector to poll
  3. Check `GET /api/telemetry/summary` for Fusion data
- **Expected result:** Fusion probe readings appear in telemetry summary within 5 minutes of configuration
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires valid Fusion credentials. Check API logs for collector output.

---

### TEST-037 — Background collector handles missing Fusion config gracefully

- **Requirement reference:** `api/app/services/collector.py` lines 40-42
- **User role:** System (background task)
- **Preconditions:** API running with no Fusion-configured tenants
- **Steps:**
  1. Start API stack
  2. Check API logs for collector messages after 5 minutes
- **Expected result:** Collector logs "No tenants with Fusion configured, skipping poll" — no errors or crashes
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-038 — API startup creates database tables

- **Requirement reference:** `api/app/main.py` lifespan — `init_db()`
- **User role:** System
- **Preconditions:** Fresh Postgres with no tables
- **Steps:**
  1. Drop all tables in Postgres
  2. Start API container
  3. Check API logs for "Database tables created"
  4. Verify `users`, `tenants`, `tenant_configs`, `csv_imports` tables exist
- **Expected result:** All 4 tables created automatically on startup
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Smoke test — critical for fresh deployment

---

### TEST-039 — Ingest endpoint validates API key length/format

- **Requirement reference:** `api/app/services/auth.py` — `create_api_key()`
- **User role:** Agent
- **Preconditions:** Valid API key format
- **Steps:**
  1. Examine generated API key format (starts with `rm_`, contains URL-safe base64)
  2. Attempt ingest with malformed API key
  3. Attempt ingest with expired/random API key
- **Expected result:** Invalid API keys are rejected with HTTP 401/403
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-040 — Fusion save endpoint persists to DB

- **Requirement reference:** `api/app/routers/fusion.py` — `POST /api/fusion/save`
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, Fusion discovery data available
- **Steps:**
  1. Call `POST /api/fusion/save` with `{"controller_id": "test123", "discovered_data": {"controllers": [{"name": "Test"}], "account": {}}}`
  2. Call `GET /api/tenant/config` to verify persisted
- **Expected result:** Fusion config saved. GET returns `fusion_config_configured: true` and config_json contains the discovery data.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-041 — Health check responds without DB

- **Requirement reference:** `GET /api/health` route
- **User role:** Unauthenticated
- **Preconditions:** API running, Postgres may be down
- **Steps:**
  1. Stop Postgres container
  2. Call `GET /api/health`
- **Expected result:** HTTP 200 — health check does not depend on DB
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Resilience test

---

### TEST-042 — Nemo AI without API key returns offline message

- **Requirement reference:** `api/app/routers/nemo.py` lines 258-262
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, NO Nemo API key configured
- **Steps:**
  1. Ensure tenant has no nemo_api_key and env has no nemo_api_key
  2. Send `POST /api/nemo/ask` with `{"question": "What is a reef tank?"}`
- **Expected result:** HTTP 200 with `{"answer": "Nemo AI is not configured yet. Go to Settings → AI Assistant to enter your API key.", "model": "offline"}`
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-043 — Redis caching — repeated Nemo queries use cache

- **Requirement reference:** `api/app/routers/nemo.py` lines 60-62, 141-144
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid JWT, Fusion-configured tenant
- **Steps:**
  1. Send tank-specific question to Nemo
  2. Immediately send same question again
  3. Check API logs for cache hit
- **Expected result:** Second query returns faster. Tank data is cached for 60s.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires Fusion creds

---

### TEST-044 — Web app — CSV Import page uploads and shows preview

- **Requirement reference:** `web/src/pages/CsvImportPage.tsx`
- **User role:** Authenticated
- **Preconditions:** Web app running, user logged in
- **Steps:**
  1. Login via web UI
  2. Navigate to `/csv-import`
  3. Upload a valid CSV file
- **Expected result:** Page displays file preview with headers and first 5 rows. Import ID shown. Import listed on page.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-045 — E2E: Register → Login → Dashboard renders → Logout

- **Requirement reference:** Full user flow
- **User role:** New user
- **Preconditions:** Web app + API + Postgres running
- **Steps:**
  1. Navigate to /register
  2. Create account with email, password, tenant name
  3. Verify redirect to /dashboard
  4. Verify dashboard sidebar renders with links
  5. Logout (clear token or close browser)
  6. Navigate to /dashboard — should redirect to /login
- **Expected result:** Complete registration-to-dashboard flow works. Auth persistence and clearing work correctly.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Full user journey — critical

---

### TEST-046 — Water tests endpoint returns data

- **Requirement reference:** `api/app/routers/telemetry.py` — `GET /api/telemetry/water-tests`
- **User role:** Authenticated (JWT)
- **Preconditions:** Mlog data has been synced into InfluxDB for this tenant (via background collector or immediate sync on Fusion save)
- **Steps:**
  1. Get valid JWT via login
  2. Send `GET /api/telemetry/water-tests` with Bearer token
- **Expected result:** HTTP 200 with `{"water_tests": [...]}`. Each entry has `parameter`, `value`, `unit`, `time` fields. Parameters include KH, Ca, Mg, NO3, PO4.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires Fusion credentials configured and mlog data synced

---

### TEST-047 — Water tests — empty data when no Fusion configured

- **Requirement reference:** `api/app/routers/telemetry.py`
- **User role:** Authenticated (JWT)
- **Preconditions:** Tenant has no Fusion credentials configured
- **Steps:**
  1. Register fresh tenant with no Fusion config
  2. Login and send `GET /api/telemetry/water-tests`
- **Expected result:** HTTP 200 with `{"water_tests": []}` — empty array, not an error
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-048 — Notes endpoint returns data

- **Requirement reference:** `api/app/routers/telemetry.py` — `GET /api/telemetry/notes`
- **User role:** Authenticated (JWT)
- **Preconditions:** Notes data has been synced into InfluxDB
- **Steps:**
  1. Login and send `GET /api/telemetry/notes`
- **Expected result:** HTTP 200 with `{"notes": [...]}`. Each entry has `note_id`, `type_name`, `title`, `comment`, `time`. Type names include Good, Bad, Ugly, Maintenance, Event, Basic.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-049 — Notes — empty data when no Fusion configured

- **Requirement reference:** `api/app/routers/telemetry.py`
- **User role:** Authenticated (JWT)
- **Preconditions:** Tenant has no Fusion credentials configured
- **Steps:**
  1. Register fresh tenant
  2. Login and send `GET /api/telemetry/notes`
- **Expected result:** HTTP 200 with `{"notes": []}` — empty array
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-050 — Fusion save triggers immediate water tests and notes sync

- **Requirement reference:** `api/app/routers/fusion.py` — save endpoint + collector
- **User role:** Authenticated (JWT)
- **Preconditions:** Valid Fusion credentials, controller discovered
- **Steps:**
  1. Discover Fusion controller via `POST /api/fusion/discover`
  2. Save config via `POST /api/fusion/save` with controller_id and discovered_data
  3. Immediately call `GET /api/telemetry/water-tests` and `GET /api/telemetry/notes`
- **Expected result:** Both endpoints return data from Fusion within seconds of saving. No need to wait 6 hours for background collector.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Tests the immediate sync trigger added in commit c5097cb. Requires valid Fusion credentials.

---

### TEST-051 — Water tests page renders in web UI

- **Requirement reference:** `web/src/pages/WaterTestPage.tsx`
- **User role:** Authenticated
- **Preconditions:** Web app running, user logged in, water test data available
- **Steps:**
  1. Login via web UI
  2. Click "Water Tests" in sidebar or navigate to `/water-tests`
- **Expected result:** Page renders with parameter cards for KH, Ca, Mg, NO3, PO4. Each card shows latest value prominently and a history table.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-052 — Notes page renders in web UI

- **Requirement reference:** `web/src/pages/NotesPage.tsx`
- **User role:** Authenticated
- **Preconditions:** Web app running, user logged in, notes data available
- **Steps:**
  1. Login via web UI
  2. Click "Tank Notes" in sidebar or navigate to `/notes`
- **Expected result:** Page renders with chronological notes timeline. Each note has color-coded type badge (Good=green, Bad=red, etc.), title, comment, and date.
- **Status:** [PENDING]
- **Evidence:**
- **Notes:** Requires browser

---

### TEST-053 — Water tests page shows empty state when no data

- **Requirement reference:** `web/src/pages/WaterTestPage.tsx`
- **User role:** Authenticated
- **Preconditions:** No water test data exists for tenant
- **Steps:**
  1. Login as tenant with no Fusion data
  2. Navigate to `/water-tests`
- **Expected result:** Page renders with a "No water test data available" message and guidance about configuring Fusion
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

### TEST-054 — Notes page shows empty state when no data

- **Requirement reference:** `web/src/pages/NotesPage.tsx`
- **User role:** Authenticated
- **Preconditions:** No notes data exists for tenant
- **Steps:**
  1. Login as tenant with no Fusion data
  2. Navigate to `/notes`
- **Expected result:** Page renders with a "No tank notes available" message and guidance
- **Status:** [PENDING]
- **Evidence:**
- **Notes:**

---

## Test Status Rules

- [PENDING]: Test has not been run.
- [PASS]: Test executed and expected result was observed.
- [FAIL]: Test executed and expected result was not observed.
- [BLOCKED]: Test could not be executed because of environment, missing data, or dependency.
- [SKIPPED]: Test intentionally not executed with a documented reason.
- [RETEST]: A previous failure is ready for re-validation after Cody's fix.
