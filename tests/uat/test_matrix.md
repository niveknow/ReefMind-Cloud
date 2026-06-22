# Test Matrix — ReefMind Cloud v0.1.0

## Coverage Map

| Category | Test ID | Test Name | Coverage (What It Validates) | Priority |
|----------|---------|-----------|------------------------------|----------|
| **Smoke** | TEST-001 | Health endpoint | API is alive | P0 |
| **Smoke** | TEST-038 | DB table creation | Startup completes | P0 |
| **Smoke** | TEST-041 | Health without DB | Resilience | P0 |
| **Auth** | TEST-002 | Register creates tenant | Onboarding flow | P0 |
| **Auth** | TEST-003 | Duplicate email rejected | Input validation | P1 |
| **Auth** | TEST-004 | Login valid creds | Auth flow | P0 |
| **Auth** | TEST-005 | Login invalid password | Negative path | P1 |
| **Auth** | TEST-006 | Login non-existent email | Negative path | P1 |
| **Auth** | TEST-007 | Unauthenticated rejection | Auth enforcement | P0 |
| **Auth** | TEST-008 | Ingest rejects JWT | Auth mode separation | P0 |
| **Auth** | TEST-028 | Register field validation | Input validation | P1 |
| **Auth** | TEST-029 | Login field validation | Input validation | P1 |
| **Ingest** | TEST-009 | Ingest telemetry | Data ingestion | P0 |
| **Ingest** | TEST-010 | Ingest outlets | Data ingestion | P0 |
| **Ingest** | TEST-011 | Ingest power | Data ingestion | P0 |
| **Ingest** | TEST-030 | Ingest invalid payload | Schema validation | P1 |
| **Ingest** | TEST-039 | API key validation | Security | P1 |
| **Telemetry** | TEST-012 | Telemetry summary | Data retrieval | P0 |
| **Telemetry** | TEST-013 | Outlet states | Data retrieval | P0 |
| **Telemetry** | TEST-014 | Probe history | Time-series query | P0 |
| **Tenant** | TEST-015 | Config retrieval | Settings | P0 |
| **Tenant** | TEST-016 | Update config | Settings | P0 |
| **Tenant** | TEST-017 | Nemo config | Settings | P1 |
| **Tenant** | TEST-018 | Regenerate API key | Security | P0 |
| **Fusion** | TEST-019 | Discovery empty creds | Validation | P1 |
| **Fusion** | TEST-020 | Discovery invalid creds | External API | P1 |
| **Fusion** | TEST-040 | Save fusion config | Persistence | P0 |
| **Nemo** | TEST-021 | Nemo status | Config check | P1 |
| **Nemo** | TEST-022 | General question | AI response | P1 |
| **Nemo** | TEST-023 | Tank-specific question | Context injection | P2 |
| **Nemo** | TEST-024 | Empty question | Validation | P1 |
| **Nemo** | TEST-042 | No API key | Fallback | P1 |
| **Nemo** | TEST-043 | Cache behavior | Performance | P2 |
| **CSV** | TEST-025 | CSV upload | Import flow | P0 |
| **CSV** | TEST-026 | CSV import list | History | P1 |
| **Security** | TEST-027 | Tenant isolation | Multi-tenant safety | P0 |
| **Security** | TEST-031 | Protected routes redirect | Frontend auth | P0 |
| **Web** | TEST-032 | Login form submit | Frontend flow | P0 |
| **Web** | TEST-033 | Register form | Frontend flow | P0 |
| **Web** | TEST-034 | Dashboard loads | Frontend UX | P0 |
| **Web** | TEST-035 | Settings page | Frontend UX | P0 |
| **Web** | TEST-044 | CSV import page | Frontend UX | P1 |
| **E2E** | TEST-036 | Background collector | Data pipeline | P0 |
| **E2E** | TEST-037 | Collector no config | Graceful handling | P1 |
| **E2E** | TEST-045 | Register → Login → Dashboard → Logout | Full user journey | P0 |

## Priority Legend

- **P0:** MVP-blocking — must pass before release
- **P1:** Important — should pass for a quality release
- **P2:** Nice-to-have — validates advanced features
- **P3:** Future — deferred beyond v0.1.0

## Coverage by Domain

| Domain | Total Tests | P0 | P1 | P2 |
|--------|-------------|----|----|----|
| Smoke | 3 | 3 | 0 | 0 |
| Auth | 10 | 5 | 5 | 0 |
| Ingest | 4 | 3 | 1 | 0 |
| Telemetry | 3 | 3 | 0 | 0 |
| Tenant | 4 | 3 | 1 | 0 |
| Fusion | 3 | 1 | 2 | 0 |
| Nemo | 6 | 0 | 4 | 2 |
| CSV | 2 | 1 | 1 | 0 |
| Security | 2 | 2 | 0 | 0 |
| Web | 5 | 4 | 1 | 0 |
| E2E | 3 | 2 | 1 | 0 |
| **Total** | **45** | **27** | **16** | **2** |
