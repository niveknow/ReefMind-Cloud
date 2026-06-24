# ReefMind — Data Collection Backlog Analysis

> Generated: 2026-06-21. Last updated: 2026-06-23 (v0.1.2).
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

### Currently Collected (by `cloud/api/app/services/collector.py`)

| Data | Measurement | Tags | Fields | Interval |
|------|------------|------|--------|----------|
| Probe readings | `apex_telemetry` | tenant_id, apex_id, probe_name, probe_type, unit, did | value (float) | 5min (7-day ilog backfill on first poll) |
| Outlet ON/OFF | `apex_outlet_states` | tenant_id, apex_id, outlet_name, outlet_type, device_id, device_group | state (0/1), state_display | 5min |
| Power (Watts/Amps) | `apex_power` | tenant_id, apex_id, outlet_name, channel | watts, amps | 5min |
| Water tests | `apex_water_tests` | tenant_id, apex_id, parameter, unit | value (float) | 5min (atomic replace) |
| Tank notes | `apex_logs` | tenant_id, apex_id, note_id, type_code, type_name, title, reason_code, has_comment | value, comment | 5min (atomic replace) |
| Controller info | `apex_controller_info` | tenant_id, apex_id, serial | hardware, software, timezone, name | 5min (atomic replace) |
| Fusion API limits | — | See §Fusion API Historical Data Limits below | — | — |

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

**P3 — Lower Urgency**:
- **#15 (Outlet Timeline)** — ~6-8 hr. Big UI effort, nice-to-have.
- **#8 (Multi-Controller)** — ~3-5 hr. Depends on #14 (done). Low unless user has multiple Apex units.
- **#9 (Client Consolidation)** — ~3-4 hr. Pure code health, no user-facing change.

---

---

## Fusion API Historical Data Limits

The Fusion API caps historical data differently depending on the data type. These limits affect how much history is available when a new tenant connects or when the collector restarts.

| Data | Fusion Endpoint | Max History | Collector Behavior | Configurable |
|------|----------------|-------------|-------------------|-------------|
| **Probe readings** | `/api/apex/{id}/ilog?days=N` | **7 days** (backfill) | One-time backfill on first poll via `BACKFILL_DAYS=7`; thereafter only live snapshots every 5min | Yes — `BACKFILL_DAYS` in `collector.py` |
| **Water tests** | `/api/apex/{id}/mlog?days=N` | **365 days** | Atomic re-sync every 5min cycle | Yes — `days=365` in `get_mlog()` |
| **Tank notes** | `/api/apex/{id}/log` (paginated) | **30 days** | Atomic re-sync every 5min cycle | Yes — `days=30` in `get_all_notes()` |
| **Controller info** | `/api/apex/{id}` | Current state only | Written every 5min cycle | N/A |
| **Outlet states** | `/api/apex/{id}` | Current state only | Written every 5min cycle | N/A |

**Note:** The ilog (probe history) limit of 7 days is our default, not a Fusion API hard limit. The Fusion ilog endpoint accepts higher `days` values, but we chose 7 to balance data density against API load during the initial backfill. Increase `BACKFILL_DAYS` in `collector.py` and reset `backfill_complete` in the tenant's `config_json` to pull deeper history.

---

## Issue 1: Fusion Power Monitoring — Collect Amps/Watts Per Outlet

**✅ DELIVERED v0.1.1 (June 23, 2026)**

**What was implemented:**
- Collector detects Watts/Amps probes by DID suffix (`_Watts`, `_Amps`, `_w`, `_a`)
- `write_power()` writes to `apex_power` measurement in InfluxDB
- Power collection gated behind `"power"` data-area toggle in Settings
- API endpoint exposes power data through telemetry router

**Original background (for reference):**
The Fusion API returns per-outlet power data in the `status.outputs[].status` array. Each outlet's status is an array where `status[0]` = state string (ON/AON/OFF), and additional elements contain power telemetry (watts, amps, frequency) for EnergyBar 832 outlets. The current collector only reads `status[0]`.

---

## Issue 2: Device Grouping for Outlets — Add device_id & device_group Tags

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `_get_device_group(did)` function in collector.py parses DID prefixes
- Prefix mapping: `2_`→EB832_1, `5_`→EB832_2, `3_`→Vortech, `4_`→EB8_4, `base_`→Base, `7_`→Feeder, `Cntl_`→Virtual, `1_`→Alarm
- Each outlet point tagged with `device_id` and `device_group` in InfluxDB
- `query_outlets()` returns `device_id` and `device_group` in its response

---

## Issue 3: Historical Probe Data Backfill — Expose ilog in Fusion Collector

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- On first poll per tenant, collector fetches 7 days of historical probe data from Fusion ilog API
- Writes history as telemetry points (same measurement as live data)
- Sets `backfill_complete: true` in tenant `config_json` (PostgreSQL jsonb)
- Subsequent polls skip backfill

---

## Issue 4: Collect Non-Probe Status Inputs (Feed, Alarms, Leak Sensors)

**📋 P2 — BACKLOG**

**Area:** Fusion Collector Data Enrichment
**Priority:** Low
**Difficulty:** Easy
**Estimate:** ~1-2 hours

### Background
The collector aggressively filters `status.inputs` to ONLY sensor types (Temp, pH, ORP, Cond, Salinity). This drops valuable non-probe data like:
- **Feed cycle status**: `FeedA`, `FeedB`, `FeedC`, `FeedD` with countdown timers
- **Alarm inputs**: leak sensors, overflow detectors, high-temp alerts
- **Expansion probes**: flow meters, depth sensors, PAR meters

Many of these appear as inputs with `did` prefixes that don't start with Tmp/pH/ORP/Sal/base_Cond but still carry useful numeric values.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
In the sensor-filtering section (~lines 90-118):
1. Add a new measurement type `apex_controller_inputs` for non-probe inputs
2. Store ALL inputs as this measurement, not just sensor types
3. Tag with `did` and `probe_name`, using a generic `unit: "raw"` for unknowns
4. Or: create a targeted whitelist of known non-probe DIDs on the controller

**File: `cloud/api/app/services/influx.py`**
Add `write_raw_inputs()` function (or extend the existing flow).

### Why This Matters
- Leak sensor history for Nemo alerts
- Feed cycle tracking ("last feed was 3 hours ago")
- Expansion module data visible in dashboards

---

## Issue 5: Controller System Health Tracking (Firmware, Uptime, Connectivity)

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- `get_controller_info()` added to FusionLiveClient — extracts hardware, software, serial, timezone from Fusion detail response
- New `apex_controller_info` measurement in InfluxDB with atomic-replace pattern
- New `write_controller_info()` and `query_controller_info()` in influx.py
- Collector fetches controller info every poll cycle
- New API endpoint `GET /api/telemetry/controller`
- Controller Info card on Settings page showing Hardware, Firmware, Serial, Timezone

---

## Issue 6: Collect Mlog (Water Test Results) from Fusion

**✅ DELIVERED v0.1.1 (June 23, 2026)**

**What was implemented:**
- `get_mlog()` method in FusionLiveClient
- `write_water_tests()` and `query_water_tests()` in InfluxDB service with atomic replace pattern
- Collector pulls mlog data every 5 minutes
- API endpoint `GET /api/telemetry/water-tests`
- WaterTestPage frontend component with latest-value cards and inline trend charts (TimeSeriesChart)

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
A single Fusion account can have multiple Apex controllers (e.g., one on the display tank, one on the frag tank). The current `collector.py` only polls `fusion_apex_id` — a single controller ID stored in tenant config. The Fusion discovery endpoint returns all controllers on the account.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
1. Add logic to discover all controllers via `/api/apex` at login time
2. Store discovered controller IDs in a new table or list in tenant config
3. Poll ALL controllers, each with their own probe/outlet writes tagged with the source controller ID

**File: `cloud/api/app/models/tenant.py`**
Add a `fusion_apex_ids` JSON array field to store multiple controller IDs.

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
There are THREE implementations of the Fusion API login+request logic in the cloud API:
1. `services/fusion_live.py` — `FusionLiveClient` (used by collector + live endpoints)
2. `services/fusion_discovery.py` — `FusionDiscoverer` (used during onboarding)
3. `scripts/apex_fusion_client.py` — `FusionClient` (legacy cron scripts, not in cloud API)

Each has duplicated login flow, CSRF handling, session management, and error handling.

### What Needs to Change
1. Consolidate `FusionLiveClient` and `FusionDiscoverer` into a single `FusionClient` in `services/fusion_client.py`
2. `FusionDiscoverer.discover()` becomes a method on `FusionClient`
3. `FusionLiveClient.get_live_readings()` and `get_all_outlet_states()` carry over
4. Legacy `scripts/apex_fusion_client.py` stays as-is for backward compatibility with cron scripts

---

## Issue 10: Backend Code Quality — Remove Debug Print Statements from Production Code

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- Replaced 3 `print(f"DEBUG ...")` statements in `services/influx.py:query_outlets()` with proper `log.debug()` calls
- Added `logging.getLogger(__name__)` to the module

---

## Issue 11: Backend Code Quality — Missing Error Handling for InfluxDB Write Failures

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- Wrapped all 5 write functions (`write_telemetry`, `write_outlets`, `write_power`, `write_water_tests`, `write_notes`) in try/except
- Delete steps for atomic-replace measurements (water_tests, notes) also protected
- Each failure logs with tenant context and returns 0 instead of crashing the collector cycle
- One failed measurement no longer loses all other data for that tenant

---

## Issue 12: Frontend Enhancement — Outlet Detail Panel (Power, Device, Firmware)

**📋 P2 — BACKLOG**

**Area:** Frontend / UX
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~4-6 hours

### Background
The current `OutletGrid` component shows a simple grid of outlet names with ON/OFF indicators. With Issues 1, 2, 7 done, per-outlet power data (watts, amps), device grouping, and outlet type are all available in the API — but the frontend ignores them.

### Prerequisites (all ✅)
- ⚡ Issue 1 — Power Monitoring ✅ (v0.1.1)
- 🏷️ Issue 2 — Device Grouping ✅ (v0.1.2)
- 🔌 Issue 7 — Outlet Type ✅ (v0.1.2)

### What Needs to Change

**File: `cloud/web/src/components/OutletGrid.tsx`**
1. Add a detail panel or expandable row showing:
   - Current wattage
   - Current amperage
   - Device group (EB832_1, EB832_2, etc.)
   - Outlet type (Variable, Switch, Pump)
2. Group outlets by device in the grid layout
3. Show power usage summary (total watts per EnergyBar)
4. Add power monitoring toggle (show/hide power columns)

---

## Issue 13: Frontend Enhancement — Water Test History Charts

**✅ DELIVERED v0.1.1 (June 23, 2026)**

**What was implemented:**
- `TimeSeriesChart` component imported and used in WaterTestPage
- Each parameter card (KH, Ca, Mg, NO3, PO4) shows a small inline trend chart
- Y-axis auto-scale (`scale: true`) ensures small fluctuations are visible
- Charts query from `GET /api/telemetry/water-tests` endpoint

---

## Issue 14: Fusion Collector — Tag Telemetry with Controller ID for Multi-Apex Support

**✅ DELIVERED v0.1.2 (June 23, 2026)**

**What was implemented:**
- Added `apex_id` tag to all 5 InfluxDB measurements: `apex_telemetry`, `apex_outlet_states`, `apex_power`, `apex_water_tests`, `apex_logs`
- Collector passes `fusion_apex_id` through to every write function
- `query_water_tests()` supports optional `apex_id` filter parameter
- Backward compatible — all functions accept `apex_id=""` as default
- Enables multi-controller filtering (Issue #8)

---

## Issue 15: Frontend — Historical Outlet State Timeline

**📋 P2 — BACKLOG**

**Area:** Frontend / UX
**Priority:** Low
**Difficulty:** Hard
**Estimate:** ~6-8 hours

### Background
Outlet states are stored in InfluxDB as a time-series with a field `state` (0 or 1). The frontend only shows current states. A timeline view showing WHEN an outlet changed state over the last 24h would help with troubleshooting equipment.

### What Needs to Change

**File: `cloud/web/src/components/OutletGrid.tsx`** or new component `OutletTimeline.tsx`**
1. Add a timeline toggle per outlet
2. Query `apex_outlet_states` with a state-change detection query
3. Show a horizontal bar: green = on, gray = off, over 24h window
4. Highlight state transitions with timestamps

**InfluxDB query pattern:**
```flux
from(bucket: "reefmind_{tenant_id}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "apex_outlet_states" and r.outlet_name == "Return_Pump")
  |> filter(fn: (r) => r._field == "state")
  |> difference()
  |> filter(fn: (r) => r._value != 0)  // only state changes
```
