# API Contract Tests — ReefMind Cloud v0.1.0

## Purpose

Validate that implemented API behavior matches the specification in the source code. Each test verifies route existence, method correctness, auth requirements, required fields, validation, success shape, and error shape.

---

### API-001 — Health

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/health |
| Auth | None |
| Success (200) | `{"status": "ok", "service": "reefmind-api", "version": "0.1.3"}` |
| Error | N/A |

### API-002 — Register

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/auth/register |
| Auth | None |
| Required fields | email, password |
| Success (200/201) | `{"access_token": "...", "tenant_id": "...", "user_id": "..."}` |
| Duplicate email (409) | `{"detail": "Email already registered"}` |
| Validation (422) | Empty email, empty password, missing body |

### API-003 — Login

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/auth/login |
| Auth | None |
| Required fields | email, password |
| Success (200) | `{"access_token": "...", "tenant_id": "...", "user_id": "..."}` |
| Invalid creds (401) | `{"detail": "Invalid email or password"}` |
| Validation (422) | Empty email, empty password |

### API-004 — Ingest Telemetry

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/ingest/telemetry |
| Auth | X-API-Key (agent key, NOT JWT) |
| Required fields | readings array (each: probe_name, probe_type, value, unit) |
| Success (200) | `{"status": "ok", "writes": <int>}` |
| No API key (401) | `{"detail": "Not authenticated"}` |
| Wrong auth (403) | `{"detail": "Agent API key required"}` (when using JWT) |
| Invalid payload (422) | Validation error |

### API-005 — Ingest Outlets

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/ingest/outlets |
| Auth | X-API-Key |
| Required fields | outlets array (each: outlet_name, state, state_display) |
| Success (200) | `{"status": "ok", "writes": <int>}` |
| No API key (401) | `{"detail": "Not authenticated"}` |

### API-006 — Ingest Power

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/ingest/power |
| Auth | X-API-Key |
| Required fields | readings array (each: outlet_name, watts, channel) |
| Success (200) | `{"status": "ok", "writes": <int>}` |
| No API key (401) | `{"detail": "Not authenticated"}` |

### API-007 — Telemetry Summary

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/telemetry/summary |
| Auth | JWT Bearer |
| Success (200) | `{"readings": [...]}` (deduplicated to latest per probe) |
| No auth (401) | `{"detail": "Not authenticated"}` |

### API-008 — Telemetry Outlets

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/telemetry/outlets |
| Auth | JWT Bearer |
| Success (200) | `{"outlets": [...], "source": "agent"}` |
| No auth (401) | `{"detail": "Not authenticated"}` |

### API-009 — Probe History

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/telemetry/{probe_name} |
| Auth | JWT Bearer |
| Query params | `duration` (e.g. "24h", "7d", "30d") |
| Success (200) | `{"probe": "<name>", "data": [...]}` |
| No auth (401) | `{"detail": "Not authenticated"}` |

### API-010 — Tenant Config GET

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/tenant/config |
| Auth | JWT Bearer |
| Success (200) | `{"config": {"backend_type": "...", "fusion_config_configured": bool, "agent_api_key": "...", "nemo_configured": bool, "nemo_provider": "...", "nemo_model": "..."}}` |
| No auth (401) | `{"detail": "Not authenticated"}` |
| Notes | Secrets (fusion_pass) NOT exposed in response |

### API-011 — Tenant Config PUT

| Property | Expected |
|----------|----------|
| Method | PUT |
| Route | /api/tenant/config |
| Auth | JWT Bearer |
| Optional fields | config_json, fusion_user, fusion_pass, fusion_apex_id, nemo_api_key, nemo_provider, nemo_model |
| Success (200) | `{"status": "ok"}` |
| Config not found (404) | `{"detail": "Config not found"}` |
| No auth (401) | `{"detail": "Not authenticated"}` |

### API-012 — Regenerate Agent Key

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/tenant/regenerate-agent-key |
| Auth | JWT Bearer |
| Success (200) | `{"agent_api_key": "rm_<new_key>"}` |
| Config not found (404) | `{"detail": "Config not found"}` |

### API-013 — Fusion Discovery

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/fusion/discover |
| Auth | JWT Bearer |
| Required fields | fusion_username, fusion_password |
| Empty creds (400) | `{"detail": "Fusion username and password are required"}` |
| Invalid creds (401) | Fusion-specific error |
| Fusion API error (502) | `{"detail": "Fusion API error: ..."}` |

### API-014 — Fusion Save

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/fusion/save |
| Auth | JWT Bearer |
| Required fields | controller_id, discovered_data |
| Success (200) | `{"status": "ok", "message": "Configuration saved for controller ..."}` |
| Config not found (404) | `{"detail": "Tenant config not found"}` |

### API-015 — Fusion Status

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/fusion/status |
| Auth | JWT Bearer |
| Success (200) | `{"connected": bool, "fusion_user": "...", "fusion_apex_id": "...", "has_creds": bool, "has_apex_id": bool, "discovered": bool}` |
| Notes | Returns `connected: false` with detail if no config |

### API-016 — Fusion Readings

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/fusion/readings |
| Auth | JWT Bearer |
| Success (200) | `{"readings": [...], "source": "fusion"}` |
| Fusion error (400) | Error detail from FusionLiveError |
| Proxy error (502) | `{"detail": "Fusion live data error: ..."}` |

### API-017 — Fusion Probe History

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/fusion/history/{probe_did} |
| Auth | JWT Bearer |
| Query params | `hours` (int, max 24) |
| Success (200) | `{"probe": "<did>", "data": [...], "source": "fusion"}` |
| Notes | probe_did is the Fusion probe identifier (e.g. "base_Temp") |

### API-018 — Fusion Outlets

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/fusion/outlets |
| Auth | JWT Bearer |
| Success (200) | `{"outlets": [...], "source": "fusion"}` |

### API-019 — Nemo Status

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/nemo/status |
| Auth | JWT Bearer |
| Success (200) | `{"configured": bool, "provider": "...", "model": "...", "source": "tenant|env|none"}` |

### API-020 — Nemo Ask

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/nemo/ask |
| Auth | JWT Bearer |
| Required fields | question (non-empty string) |
| Success (200) | `{"answer": "...", "model": "..."}` |
| Empty question (400) | `{"detail": "Question cannot be empty"}` |
| No API key configured | `{"answer": "Nemo AI is not configured yet...", "model": "offline"}` |

### API-021 — CSV Upload

| Property | Expected |
|----------|----------|
| Method | POST |
| Route | /api/csv/upload |
| Auth | JWT Bearer |
| Required fields | file (multipart upload) |
| Success (200) | `{"import_id": "...", "filename": "...", "file_size": int, "headers": [...], "preview_rows": [...], "status": "pending"}` |
| Notes | Parses first 5 rows for preview |

### API-022 — CSV Imports List

| Property | Expected |
|----------|----------|
| Method | GET |
| Route | /api/csv/imports |
| Auth | JWT Bearer |
| Success (200) | `{"imports": [{"id": "...", "filename": "...", "file_size": int, "rows_imported": int, "status": "...", "created_at": "..."}]}` |
| Notes | Ordered by most recent, limited to 20 |
