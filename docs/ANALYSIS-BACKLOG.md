# ReefMind — Data Collection Backlog Analysis

> Generated: 2026-06-21. Last updated: 2026-06-24 (v0.1.4).
> Full audit of what Fusion collects vs what's possible.
> Each section is a self-contained GitHub Issue candidate.

---

## Summary: Delivery Status

| # | Issue | Status | Release | Area |
|---|-------|--------|---------|------|
| 1 | 🔌 Power Monitoring (Watts/Amps) | ✅ **Delivered** | v0.1.1 | Collector |
| 2 | 🏷️ Device Grouping (device_id/device_group) | ✅ **Delivered** | v0.1.2 | Collector |
| 3 | 📦 Historical ilog Backfill | ✅ **Delivered** | v0.1.2 | Collector |
| 4 | 📡 Non-Probe Inputs (Feed, Alarms) | 📋 P2 — Open | — | Collector |
| 5 | 🖥️ Controller System Health | ✅ **Delivered** | v0.1.2 | Collector + UI |
| 6 | 🧪 Water Tests (Mlog) | ✅ **Delivered** | v0.1.1 | Collector |
| 7 | 🔌 Store Outlet Type | ✅ **Delivered** | v0.1.2 | Collector |
| 8 | 🔄 Multi-Controller Support | 📋 P3 — Open | — | Collector |
| 9 | 🛠️ Client Consolidation | 📋 P3 — Open | — | Code Quality |
| 10 | 🧹 Remove Debug Prints | ✅ **Delivered** | v0.1.2 | Code Quality |
| 11 | 🛡️ Error Handling for Writes | ✅ **Delivered** | v0.1.2 | Code Quality |
| 12 | 📊 Outlet Detail Panel | 📋 P2 — Open | — | Frontend |
| 13 | 📊 Water Test Charts | ✅ **Delivered** | v0.1.1 | Frontend |
| 14 | 🏷️ Controller ID Tag | ✅ **Delivered** | v0.1.2 | Schema |
| 15 | 📊 Outlet State Timeline | 📋 P2 — Open | — | Frontend |
| — | 🐛 Route Ordering Fix | ✅ **Delivered** | v0.1.2 | Bugfix |
| — | 🐛 Duration Button Fix | ✅ **Delivered** | v0.1.2 | Bugfix |
| — | 📄 Fusion API Limits Doc | ✅ **Delivered** | v0.1.2 | Docs |
| — | 🗒️ Full Notes Backfill (18 months) | ✅ **Delivered** | v0.1.3 | Collector |
| — | 🗒️ Notes Month/Week Filter | ✅ **Delivered** | v0.1.4 | Frontend |
| — | 🗒️ 730d Notes History | ✅ **Delivered** | v0.1.4 | API |
| — | 🤖 Nemo Notes Insights (2yr / 50 notes) | ✅ **Delivered** | v0.1.4 | Nemo |
| — | 🐛 Empty Note Titles Fix | ✅ **Delivered** | v0.1.4 | Bugfix |
| — | 🐛 Notes API 100-Limit Removed | ✅ **Delivered** | v0.1.4 | Bugfix |

### Currently Collected (by `cloud/api/app/services/collector.py`)

| Data | Measurement | Tags | Fields | Interval | History |
|------|------------|------|--------|----------|---------|
| Probe readings | `apex_telemetry` | tenant_id, apex_id, probe_name, probe_type, unit, did | value (float) | 5min | 7-day ilog backfill on first poll |
| Outlet ON/OFF | `apex_outlet_states` | tenant_id, apex_id, outlet_name, outlet_type, device_id, device_group | state (0/1), state_display | 5min | Current state |
| Power (Watts/Amps) | `apex_power` | tenant_id, apex_id, outlet_name, channel | watts, amps | 5min | Current readings |
| Water tests | `apex_water_tests` | tenant_id, apex_id, parameter, unit | value (float) | 5min (atomic replace) | 365 days |
| Tank notes | `apex_logs` | tenant_id, apex_id, note_id, type_code, type_name, title, reason_code, has_comment | value, comment | 5min (atomic replace) | **18 months backfilled** (API returns 730d) |
| Controller info | `apex_controller_info` | tenant_id, apex_id, serial | hardware, software, timezone, name | 5min (atomic replace) | Current state |

### Available from Fusion But NOT Collected

| Data | Fusion Source | Impact | Issue |
|------|-------------|--------|-------|
| Feed cycle state | status.inputs | No feed mode awareness | #4 |
| Alarm status | status.inputs (non-probe) | No alerting | #4 |
| Non-probe inputs | status.inputs (leak sensors, flow, etc.) | Lost data for expansion modules | #4 |
| Fusion account/controller list | /api/apex, /api/account | No multi-controller awareness | #8 |

---

### Current Backlog Priority (What's Left)

**P2 — Worth Doing** (next candidates):
- **#4 (Non-Probe Inputs)** — ~1-2 hr. Collects feed/alarm/leak/flow data. Niche but useful for Nemo alerts.
- **#12 (Outlet Detail Panel)** — ~4-6 hr. UI for power/device/type. Depends on #1, #2, #7 (all done). Self-service now.
- **#15 (Outlet Timeline)** — ~6-8 hr. Historical state change visualization per outlet.

**P3 — Lower Urgency**:
- **#8 (Multi-Controller)** — ~3-5 hr. Depends on #14 (done). Low unless user has multiple Apex units.
- **#9 (Client Consolidation)** — ~3-4 hr. Pure code health, no user-facing change.

---

## Fusion API Historical Data Limits

The Fusion API caps historical data differently depending on the data type.

| Data | Fusion Endpoint | Max History | Collector Behavior | Configurable |
|------|----------------|-------------|-------------------|-------------|
| **Probe readings** | `/api/apex/{id}/ilog?days=N` | **7 days** (backfill) | One-time backfill on first poll; thereafter only live snapshots every 5min | Yes — `backfill_days` in tenant config_json |
| **Water tests** | `/api/apex/{id}/mlog?days=N` | **365 days** | Atomic re-sync every 5min cycle | Yes — `days=365` in `get_mlog()` |
| **Tank notes** | `/api/apex/{id}/notes` (paginated) | **18 months** (backfilled) | Monthly-chunked backfill on first poll (30-540d in 30d steps); daily 30d cycle thereafter | Backfill auto-runs on first poll; 30d regular window |
| **Controller info** | `/api/apex/{id}` | Current state only | Written every 5min cycle | N/A |
| **Outlet states** | `/api/apex/{id}` | Current state only | Written every 5min cycle | N/A |

**Note:** Probe backfill uses the Fusion `/logs` endpoint (7-day chunks, limited to `min(backfill_days, 7)` per tenant config). Notes backfill uses the `/notes` endpoint with monthly paginated windows.

---

## Issue 1: Fusion Power Monitoring — Collect Amps/Watts Per Outlet

**✅ DELIVERED v0.1.1 (June 23, 2026)**

**What was implemented:**
- Collector detects Watts/Amps probes by DID suffix (`_Watts`, `_Amps`, `_w`, `_a`)
- `write_power()` writes to `apex_power` measurement in InfluxDB
- Power collection gated behind `"power"` data-area toggle in Settings
- API endpoint exposes power data through telemetry router

---

## Issue 2: Device Grouping for Outlets — Add device_id & device_group Tags

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `_get_device_group(did)` function in collector.py parses DID prefixes
- Prefix mapping: `2_`→EB832_1, `5_`→EB832_2, `3_`→Vortech, `4_`→EB8_4, `base_`→Base, `7_`→Feeder, `Cntl_`→Virtual, `1_`→Alarm
- Each outlet point tagged with `device_id` and `device_group` in InfluxDB

---

## Issue 3: Historical Probe Data Backfill — Expose ilog in Fusion Collector

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- On first poll per tenant, collector fetches 7 days of historical probe data from Fusion ilog API
- Writes history as telemetry points (same measurement as live data)
- Sets `backfill_complete: true` in tenant `config_json` (PostgreSQL jsonb)

---

## Issue 4: Collect Non-Probe Status Inputs (Feed, Alarms, Leak Sensors)

**📋 P2 — BACKLOG**

**Area:** Fusion Collector Data Enrichment
**Priority:** Low
**Difficulty:** Easy
**Estimate:** ~1-2 hours

### Background
The collector aggressively filters `status.inputs` to ONLY sensor types (Temp, pH, ORP, Cond, Salinity). This drops valuable non-probe data like feed cycles, alarm inputs, and expansion probes.

### What Needs to Change
**File: `cloud/api/app/services/collector.py`** — Store all inputs as a new measurement `apex_controller_inputs`, tagged with `did` and `probe_name`.

**File: `cloud/api/app/services/influx.py`** — Add `write_raw_inputs()` function.

### Why This Matters
- Leak sensor history for Nemo alerts
- Feed cycle tracking ("last feed was 3 hours ago")
- Expansion module data visible in dashboards

---

## Issue 5: Controller System Health Tracking (Firmware, Uptime, Connectivity)

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `get_controller_info()` — extracts hardware, software, serial, timezone from Fusion detail
- New `apex_controller_info` measurement in InfluxDB with atomic-replace
- New API endpoint `GET /api/telemetry/controller`
- Controller Info card on Settings page

---

## Issue 6: Collect Mlog (Water Test Results) from Fusion

**✅ DELIVERED v0.1.1 (June 23, 2026)**

**What was implemented:**
- `get_mlog()` method in FusionLiveClient
- `write_water_tests()` and `query_water_tests()` in InfluxDB with atomic replace
- Collector pulls mlog data every 5 minutes
- `GET /api/telemetry/water-tests` endpoint
- WaterTestPage with inline trend charts

---

## Issue 7: Fusion Collector Should Store Outlet Type from Config

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `outlet_type` tag added to `apex_outlet_states` measurement
- Collector pulls `type` from Fusion `config.outputs[]` (Variable, Switch, Pump, Heater)
- `query_outlets()` returns `outlet_type` in response

---

## Issue 8: Fan-out Collector Polls to All Discovered Controllers

**📋 P3 — BACKLOG**

**Area:** Fusion Collector Multi-Controller
**Priority:** Low
**Difficulty:** Medium
**Estimate:** ~3-5 hours

### Background
A single Fusion account can have multiple Apex controllers. Current collector only polls `fusion_apex_id`. Discovery endpoint returns all controllers.

### Prerequisites
- ✅ Issue #14 (Controller ID tag) — done in v0.1.2

---

## Issue 9: Backend Code Quality — Deduplicate Fusion Client Implementations

**📋 P3 — BACKLOG**

**Area:** Code Architecture / Tech Debt
**Priority:** Low
**Difficulty:** Medium
**Estimate:** ~3-4 hours

### Background
Three implementations of Fusion API login+request logic exist:
1. `services/fusion_live.py` — `FusionLiveClient`
2. `services/fusion_discovery.py` — `FusionDiscoverer`
3. `scripts/apex_fusion_client.py` — legacy cron client

### What Needs to Change
Consolidate into a single `FusionClient` in `services/fusion_client.py`.

---

## Issue 10: Backend Code Quality — Remove Debug Print Statements

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- Replaced 3 `print(f"DEBUG ...")` statements with proper `log.debug()` calls
- Added `logging.getLogger(__name__)` to the module

---

## Issue 11: Backend Code Quality — Missing Error Handling for InfluxDB Write Failures

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- Wrapped all 5 write functions in try/except
- Delete steps for atomic-replace measurements protected
- Each failure logs with tenant context and returns 0

---

## Issue 12: Frontend Enhancement — Outlet Detail Panel (Power, Device, Firmware)

**📋 P2 — BACKLOG**

**Area:** Frontend / UX
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~4-6 hours

### Prerequisites (all ✅)
- ⚡ Issue 1 — Power Monitoring ✅ (v0.1.1)
- 🏷️ Issue 2 — Device Grouping ✅ (v0.1.2)
- 🔌 Issue 7 — Outlet Type ✅ (v0.1.2)

### What Needs to Change
Add expandable outlet detail panel showing wattage, amperage, device group, outlet type, grouped by device with power usage summary.

---

## Issue 13: Frontend Enhancement — Water Test History Charts

**✅ DELIVERED v0.1.1 (June 23, 2026)**

---

## Issue 14: Fusion Collector — Tag Telemetry with Controller ID for Multi-Apex Support

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `apex_id` tag added to all 5 InfluxDB measurements
- Collector passes `fusion_apex_id` through to every write function
- Enables multi-controller filtering (Issue #8)

---

## Issue 15: Frontend — Historical Outlet State Timeline

**📋 P2 — BACKLOG**

**Area:** Frontend / UX
**Priority:** Low
**Difficulty:** Hard
**Estimate:** ~6-8 hours

### Background
Outlet states stored in InfluxDB as time-series. A timeline view showing WHEN an outlet changed state would help with troubleshooting.

### What Needs to Change
Add timeline toggle per outlet with InfluxDB state-change detection query.

---

## v0.1.3 — New Items: Full Notes Backfill

The following items were delivered in v0.1.3 (not in the original 15-issue backlog):

### Notes Backfill (18 Months)
**Status:** ✅ Delivered v0.1.3

Monthly-chunked backfill pulls notes from Fusion API across 18 monthly windows (30–540 days back), deduplicates by `note_id`, and writes via InfluxDB HTTP API to bypass stale Python client connection pool.

### Historical Probe Backfill (90 Days)
**Status:** ✅ Delivered v0.1.3

Extended from 7-day default to 90-day chunked backfill using Fusion `/logs` endpoint with 7-day windows. Configurable via `backfill_days` in tenant `config_json`.

### Nemo AI Context Enrichment
**Status:** ✅ Delivered v0.1.3

Injected full water test history (365d), probe trends (24h/7d/30d/90d), and recent notes into Nemo system prompt for personalized advice.

---

## v0.1.4 — New Items: Notes History & Nemo Insights

The following items were delivered in v0.1.4:

### Notes Month/Week Filter Page
**Status:** ✅ Delivered v0.1.4 — Frontend

Filter bar on Tank Notes page with time presets (All, 1Y, 6M, 3M, This Month, This Week), month-jump dropdown, and month-grouped display with counts.

### 730d Notes History (API)
**Status:** ✅ Delivered v0.1.4 — API

Default `query_notes()` duration extended to 730d (24 months). 100-note limit removed so all notes in range are returned.

### Nemo Notes Insights
**Status:** ✅ Delivered v0.1.4 — Nemo

Nemo now receives 2 years / 50 notes with full comment text. Can answer questions like "what corals did I buy this year" or "show me all maintenance in January".

### Empty Note Titles Fix
**Status:** ✅ Delivered v0.1.4 — Bugfix

Notes with empty titles (e.g. Maintenance/Changed Media with no manual title) caused InfluxDB HTTP 400 on line protocol writes. Fixed by resolving via `REASON_TITLES` mapping.
