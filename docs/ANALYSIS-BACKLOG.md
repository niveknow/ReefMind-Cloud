# ReefMind — Data Collection Backlog Analysis

> Generated: 2026-06-21. Full audit of what Fusion collects vs what's possible.
> Each section is a self-contained GitHub Issue candidate.

---

## Summary: What We Collect vs What Fusion Makes Available

### Currently Collected (by `cloud/api/app/services/collector.py`)

| Data | Measurement | Tags | Fields | Interval |
|------|------------|------|--------|----------|
| Probe readings | `apex_telemetry` | tenant_id, probe_name, probe_type, unit, did | value (float) | 5min |
| Outlet ON/OFF | `apex_outlet_states` | tenant_id, outlet_name | state (0/1), state_display | 5min |

### Available from Fusion But NOT Collected

| Data | Fusion Source | Impact |
|------|-------------|--------|
| Outlet power (watts, amps) | status.outputs[].status[1..3] | No energy monitoring in dashboard |
| Device grouping | config.outputs[].did prefix | Can't show which EB832/device outlets belong to |
| Outlet type info | config.outputs[].type | No outlet category context in UI |
| Feed cycle state | status.inputs | No feed mode awareness |
| Alarm status | status.inputs (non-probe) | No alerting |
| Historical ilog data | /api/apex/{id}/ilog | Gaps when collector is restarted/changed |
| Mlog (water tests) | /mlog endpoint | No KH/Ca/Mg tracking |
| Tank notes | /log endpoint | No observation history |
| Controller health info | detail.hardware, detail.software, detail.serial | No firmware tracking |
| Non-probe inputs | status.inputs (leak sensors, flow, etc.) | Lost data for expansion modules |
| Fusion account/controller list | /api/apex, /api/account | No multi-controller awareness |

---

## Issue 1: Fusion Power Monitoring — Collect Amps/Watts Per Outlet

**Area:** Fusion Collector Data Enrichment
**Priority:** High — user-facing energy tracking
**Difficulty:** Medium
**Estimate:** ~3-4 hours

### Background
The Fusion API returns per-outlet power data in the `status.outputs[].status` array. Each outlet's status is an array where `status[0]` = state string (ON/AON/OFF), and additional elements contain power telemetry (watts, amps, frequency) for EnergyBar 832 outlets. The current collector only reads `status[0]`.

### What Fusion Returns
```json
{
  "did": "2_1",
  "status": ["AON", 120, 3.5, 60]
  //         state, watts, amps, freq
}
```

The EnergyBar 832 reports **watts** (index 1) and **amps** (index 2) for monitored outlets. Non-monitored outlets (EB8, standard relays) only have `["AON"]` or `["OFF"]`.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
In `_collect_tenant()`, section 2 (Outlet states, ~line 126-146):
1. After extracting `state_arr`, read additional elements:
   - `state_arr[1]` = watts (float) if present and parseable
   - `state_arr[2]` = amps (float) if present and parseable
2. Write power data to `apex_power` measurement using the existing `write_power()` function

**File: `cloud/api/app/services/influx.py`**
The `write_power()` function already exists with correct schema:
- Measurement: `apex_power`
- Tags: tenant_id, outlet_name, channel
- Fields: watts, amps
- The channel tag should be the outlet's DID (e.g. "2_1")

**File: `cloud/api/app/services/fusion_live.py`**
In `get_all_outlet_states()`, return the raw status array untouched so the collector can parse it.

### Verify
```python
# After fix, collector log should show power writes
# Expected: "Tenant abc123: 8 readings, 32 outlets, 18 power channels"
# Confirm InfluxDB: from(bucket:"reefmind_...") |> range(start:-10m) |> filter(fn: (r) => r._measurement == "apex_power")
```

### Pitfalls
- Some outlets won't have power data — handle gracefully with None/fallback
- EnergyBar 832 reports 120V/60Hz baseline on some regions — don't mistake frequency for power
- Existing `write_power()` signature expects `outlet_name`, `watts`, `amps`, `channel` — map correctly
- Collector currently has no `write_power()` call — must import and invoke it

---

## Issue 2: Device Grouping for Outlets — Add device_id & device_group Tags

**Area:** Fusion Collector Data Enrichment
**Priority:** Medium
**Difficulty:** Easy
**Estimate:** ~1 hour

### Background
The local collector (`apex_unified_scraper.py`) tags each outlet state with `device_id` and `device_group` using `get_device_group()` to map the DID prefix to a human-readable group (EB832_1, EB832_2, EB8_4, Vortech, Base, Virtual, Alarm, Feeder, Other). This enables dashboard filters like "show only EnergyBar outlets" or "hide virtual outlets." The Fusion collector has no equivalent tagging.

### The DID Prefix Convention
| DID prefix | Device Group | Example |
|------------|-------------|---------|
| `2_` | EB832_1 | `2_1`, `2_2` |
| `5_` | EB832_2 | `5_1` |
| `4_` | EB8_4 | `4_1` |
| `3_` | Vortech | `3_1` |
| `base_` | Base | `base_Out1` |
| `7_` | Feeder | `7_1` |
| `Cntl_` | Virtual | `Cntl_Virtual` |
| `1_` | Alarm | `1_1` |

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
Add a `get_device_group(did)` function (or import equivalent) and attach `device_id` and `device_group` tags to outlet InfluxDB points.

**File: `cloud/api/app/services/influx.py`**
Update `write_outlets()` — add optional `device_id` and `device_group` tags to the `apex_outlet_states` Point.

### Why This Matters
- Dashboard could show "Outlet Status by Device" grid
- Users can hide virtual/feeder/alarm outlets in charts
- Nemo context can reference physical vs virtual outlets

---

## Issue 3: Historical Probe Data Backfill — Expose ilog in Fusion Collector

**Area:** Fusion Collector Data Enrichment
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~4-6 hours

### Background
Fusion's `/api/apex/{id}/ilog?days=N` endpoint returns 10-minute resolution historical probe data going back ~7 days (Fusion caps ilog at 7 days). The existing cron scripts (`apex_fusion_ilog_sync.py`) already use this, but it runs as a separate weekly cron in the legacy Docker setup — the cloud Fusion collector never calls it.

The current collector only takes point-in-time snapshots every 5 minutes. If the collector was down for 30 minutes, there's a gap. The ilog endpoint provides a backfill mechanism.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
On the first poll for a tenant (first run ever), call `/ilog?days=7` to backfill the last 7 days of probe data with 10-minute resolution before starting 5-minute live polling.

Or run ilog backfill as part of the tenant onboarding flow in the discovery step.

**File: `cloud/api/app/services/fusion_live.py`**
The `get_probe_history()` method exists but is never called by the collector. It returns per-probe history — we need to adapt it for bulk backfill (all probes at once).

### Verify
```python
# After backfill: check for non-empty ilog history in InfluxDB
# from(bucket:"reefmind_...") |> range(start:-7d) |> filter(fn: (r) => r._measurement == "apex_telemetry") |> count()
# Count should be > (5min interval * 7 days = ~2016 points per probe) * N probes
# With ilog (10min res): ~1008 points per probe * N probes
```

### Pitfalls
- Fusion's ilog endpoint rejects days >= 10 — cap at 7
- InfluxDB dedup handles overlapping time ranges, but use idempotent writes
- Rate-limit: don't hammer ilog on every poll — once at onboarding is enough
- Could add a `backfill_complete` flag to tenant config in Postgres

---

## Issue 4: Collect Non-Probe Status Inputs (Feed, Alarms, Leak Sensors)

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

**Area:** Fusion Collector Data Enrichment
**Priority:** Low
**Difficulty:** Easy
**Estimate:** ~1 hour

### Background
The `/api/apex/{id}` response includes system metadata like `hardware`, `software` (firmware), `serial`, and `timezone`. The local collector tracks controller uptime/connectivity in `apex_controller_status`. The Fusion collector has none of this.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`**
On each poll, log the hardware/software versions. If they change from previously stored values (in tenant config or dedicated measurement), flag it.

Add a new measurement `apex_controller_info` with:
- Tags: tenant_id, apex_id
- Fields: hardware (str), software (str), serial (str), timezone (str)
- This is a once-per-run write unless values change

### Why This Matters
- Users get notified when firmware changes
- Dashboard shows controller model/serial
- Multi-controller deployments can identify which Apex is which

---

## Issue 6: Collect Mlog (Water Test Results) from Fusion

**Area:** Fusion Collector Data Enrichment
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~3-4 hours

### Background
The legacy cron container runs `apex_mlog_sync.py` to pull water test results (KH, Ca, Mg, NO3, PO4) from Fusion's `/mlog` endpoint. The cloud collector does not. This means manually-entered water tests from the Fusion dashboard or Apex display are invisible in ReefMind.

### What Needs to Change

**File: `cloud/api/app/services/collector.py`** (or new dedicated sync script)
Add an `/mlog` poll that fetches recent water test results and stores them in a new InfluxDB measurement `apex_water_tests` with:
- Tags: tenant_id, parameter (KH/Ca/Mg/NO3/PO4)
- Fields: value, unit
- Time: from the log entry timestamp

This could run less frequently (every 6h) since water tests are entered manually.

### API Endpoint
```python
resp = client._get(f"/api/apex/{apex_id}/mlog?days=30")
# Returns list of {date, name, value, unit}
```

### Verify
- Check InfluxDB: `from(bucket: "reefmind_...") |> range(start:-30d) |> filter(fn: (r) => r._measurement == "apex_water_tests")`
- Dashboard trend charts for KH/Ca/Mg over time

---

## Issue 7: Fusion Collector Should Store Outlet Type from Config

**Area:** Fusion Collector Data Enrichment
**Priority:** Low
**Difficulty:** Easy
**Estimate:** ~30 minutes

### Background
`config.outputs` has a `type` field per outlet (e.g. "Variable", "Switch", "Pump", "Heater"). The collector ignores it. This type indicates the physical device class and could inform dashboard UI (show a dimmer slider for Variable outlets, a toggle for Switch).

### What Needs to Change

**File: `cloud/api/app/services/influx.py`**
Add `outlet_type` as a tag on the `apex_outlet_states` Point.

**File: `cloud/api/app/services/collector.py`**
Pass `out.get("type", "")` from config_outputs into the outlet point.

---

## Issue 8: Fan-out Collector Polls to All Discovered Controllers

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

---

## Issue 9: Backend Code Quality — Deduplicate Fusion Client Implementations

**Area:** Code Architecture / Tech Debt
**Priority:** Medium
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

### Pitfalls
- `fusion_live.py` uses `request` module directly; `fusion_discovery.py` does too — similar but not identical error handling
- `fusion_discovery.py` has a richer `discover()` method that calls `/api/account`, `/api/apex`, and per-controller detail
- Must ensure all call sites are updated: `routers/telemetry.py`, `routers/nemo.py`, `routers/fusion.py`

---

## Issue 10: Backend Code Quality — Remove Debug Print Statements from Production Code

**Area:** Code Quality / Cleanup
**Priority:** Low
**Difficulty:** Trivial
**Estimate:** ~15 minutes

### Background
`services/influx.py` has `print(f"DEBUG ...")` statements in `query_outlets()` (~lines 121, 131, 141). These were added during the outlet-display debugging session. They leak internal state to stdout and shouldn't be in production code.

### What Needs to Change
Replace `print(f"DEBUG query_outlets: ...")` with `log.debug("query_outlets: ...")` using the module's logger.

### Files
- `cloud/api/app/services/influx.py` — lines 121, 131, 141

---

## Issue 11: Backend Code Quality — Missing Error Handling for InfluxDB Write Failures

**Area:** Code Quality / Resilience
**Priority:** Medium
**Difficulty:** Easy
**Estimate:** ~1 hour

### Background
`write_telemetry()`, `write_outlets()`, and `write_power()` in `services/influx.py` have no error handling. If InfluxDB is down or the bucket doesn't exist, the function throws an unhandled exception that propagates up through the collector loop and (in the worst case) crashes the collector for that tenant.

The collector's exception handler at line 150 catches this with a generic `except Exception` — but the damage is already done: the entire tenant cycle fails.

### What Needs to Change

**File: `cloud/api/app/services/influx.py`**
Wrap each `write_api.write()` call in try/except and:
1. Log the error with context (tenant_id, measurement, point count)
2. Re-raise only for truly fatal errors (auth failure)
3. Return 0 for transient failures (connection refused, timeout)

**Alternative:** The `ensure_tenant_bucket()` function does handle bucket auto-creation, but the write itself has no retry.

---

## Issue 12: Frontend Enhancement — Outlet Detail Panel (Power, Device, Firmware)

**Area:** Frontend / UX
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~4-6 hours
**Depends on:** Issue 1 (Power Monitoring), Issue 2 (Device Grouping)

### Background
The current `OutletGrid` component shows a simple grid of outlet names with ON/OFF indicators. With Issues 1, 2, 7 done, we'd have per-outlet power data (watts, amps), device grouping, and outlet type — all of which the frontend ignores.

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

**New endpoint needed:**
`GET /api/telemetry/power?tenant_id={id}` — returns current wattage per outlet (could share the `apex_power` measurement)

---

## Issue 13: Frontend Enhancement — Water Test History Charts

**Area:** Frontend / UX
**Priority:** Medium
**Difficulty:** Medium
**Estimate:** ~4-5 hours
**Depends on:** Issue 6 (Mlog Collection)

### Background
The Dashboard only shows live probe readings and outlet states. Water test parameters (KH, Ca, Mg, NO3, PO4) are collected but have no UI. Users currently must use Grafana (separate service) to view these trends.

### What Needs to Change

**New component:** `WaterTestChart.tsx`
1. Fetch from new `/api/telemetry/water-tests?tenant_id={id}&duration=30d`
2. Show time-series for each parameter as separate line charts
3. Add parameter selector (which params to show)
4. Show latest values as cards above chart

**New API endpoint:** `GET /api/telemetry/water-tests` in `routers/telemetry.py`

---

## Issue 14: Fusion Collector — Tag Telemetry with Controller ID for Multi-Apex Support

**Area:** Fusion Collector / Schema
**Priority:** Low
**Difficulty:** Easy
**Estimate:** ~30 minutes
**Depends on:** Issue 8 (Multi-Controller)

### Background
All telemetry points are tagged only with `tenant_id` and `probe_name`. If a tenant has multiple Apex controllers, there's no way to distinguish which controller a reading came from. InfluxDB queries would return merged data.

### What Needs to Change
Add `apex_id` as a tag to `apex_telemetry`, `apex_outlet_states`, and `apex_power` measurements in the collector. The `apex_id` value comes from `tcfg["fusion_apex_id"]`.

**File: `cloud/api/app/services/collector.py`**
Pass `apex_id` through to all InfluxDB write calls.

**File: `cloud/api/app/services/influx.py`**
Update all write functions to accept an optional `apex_id` tag parameter.

---

## Issue 15: Frontend — Historical Outlet State Timeline

**Area:** Frontend / UX
**Priority:** Low
**Difficulty:** Hard
**Estimate:** ~6-8 hours

### Background
Outlet states are stored in InfluxDB as a time-series with a field `state` (0 or 1). The frontend only shows current states. A timeline view showing WHEN an outlet changed state over the last 24h would help with troubleshooting equipment.

### What Needs to Change

**File: `cloud/web/src/components/OutletGrid.tsx`** or new component `OutletTimeline.tsx`
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

---

## Summary: Priority Order for Implementation

| Order | Issue | Value | Effort |
|-------|-------|-------|--------|
| 1 | ⚡ Issue 1 — Power Monitoring | High | Medium |
| 2 | ⚡ Issue 2 — Device Grouping | Medium | Easy |
| 3 | ⚡ Issue 6 — Water Tests (Mlog) | Medium | Medium |
| 4 | 🛠 Issue 9 — Client Consolidation | Medium | Medium |
| 5 | 🛠 Issue 11 — Write Error Handling | Medium | Easy |
| 6 | 📊 Issue 12 — Outlet Detail Panel | Medium | Medium |
| 7 | 🛠 Issue 10 — Remove Debug Prints | Low | Trivial |
| 8 | 📦 Issue 3 — Historical ilog Backfill | Medium | Medium |
| 9 | 📊 Issue 13 — Water Test Charts | Medium | Medium |
| 10 | 🛠 Issue 7 — Store Outlet Type | Low | Easy |
| 11 | 📊 Issue 15 — Outlet Timeline | Low | Hard |
| 12 | 📦 Issue 4 — Non-Probe Inputs | Low | Easy |
| 13 | 🛠 Issue 14 — Controller ID Tag | Low | Easy |
| 14 | 📦 Issue 5 — System Health | Low | Easy |
| 15 | 📦 Issue 8 — Multi-Controller | Low | Medium |
