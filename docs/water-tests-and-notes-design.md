# Water Tests & Tank Notes — Integration Design

> **Author:** Archie (SaaS Architect)
> **Date:** 2026-06-22
> **Status:** Design for implementation
> **Source:** Ported from on-prem `apex_mlog_sync.py` and `apex_notes.py` patterns

---

## 1. Overview

ReefMind on-prem (ReefMind project) already handles water test data (mlog) and tank notes from Apex Fusion through two dedicated sync scripts and a shared notes library:

- `scripts/apex_mlog_sync.py` — Fetches water test results from Fusion mlog API, writes to InfluxDB
- `scripts/apex_notes.py` — Shared note type definitions and InfluxDB point conversion
- `scripts/apex_fusion_log_sync.py` — Fetches tank notes from Fusion notes API

These scripts use the existing `FusionClient` from `scripts/apex_fusion_client.py` which provides:
- `client.get_mlog(apex_id, days=365)` → list of `{type, value, date}`
- `client.get_notes_page(apex_id, date_str, page, per_page)` → `[metadata, notes_list]`

**Goal:** Port this functionality into ReefMind-Cloud so users can see their water tests and tank notes in the dashboard.

---

## 2. Fusion API References

### Water Tests (mlog)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/apex/{apex_id}/mlog?days={days}` | GET | Returns list of water test results |

**Response format:** `[{type: int, value: number, date: string}, ...]`

**Type mapping:**
| Code | Parameter | Unit |
|------|-----------|------|
| 1 | KH | dkh |
| 2 | Ca | ppm |
| 3 | I | ppm (skipped — iodine not useful) |
| 4 | Mg | ppm |
| 5 | NO3 | ppm |
| 6 | PO4 | ppm |

**Source:** `scripts/apex_mlog_sync.py`

### Tank Notes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/apex/{apex_id}/notes?date={iso}&page={n}&per_page={n}` | GET | Returns paginated notes |

**Response format:** `[metadata_dict, notes_list]`

**Note fields:** `id`, `date`, `type` (int), `reason` (int), `title` (str), `text` (str)

**Type mapping:**
| Code | Name |
|------|------|
| 0 | Basic |
| 1 | Good |
| 2 | Bad |
| 3 | Ugly |
| 4 | Maintenance |
| 5 | Event |

**Reason titles:** 20+ reason codes for specific events (e.g., Water Change, Fish Died, Added Coral, Dosed...)

**Source:** `scripts/apex_notes.py`, `scripts/apex_fusion_client.py`

---

## 3. ReefMind-Cloud Implementation

### 3.1 FusionLiveClient — Add mlog and notes methods

**File:** `api/app/services/fusion_live.py`

Add to `FusionLiveClient`:

```python
def get_mlog(self, apex_id: str, days: int = 365) -> list[dict]:
    """Fetch water test results from Fusion mlog API.
    
    Returns: list of {type, value, date}
    """
    resp = self._get(f"/api/apex/{apex_id}/mlog?days={days}")
    return resp.json()

def get_notes(self, apex_id: str, date_str: str = "",
              page: int = 1, per_page: int = 200) -> list:
    """Fetch tank notes from Fusion notes API.
    
    Returns: [metadata, notes_list]
    """
    import time
    ts = int(time.time() * 1000)
    url = f"/api/apex/{apex_id}/notes?page={page}&per_page={per_page}&_={ts}"
    if date_str:
        url += f"&date={date_str}"
    resp = self._get(url)
    return resp.json()
```

### 3.2 Collector — Add mlog and notes sync

**File:** `api/app/services/collector.py`

The collector currently runs every 300s (5 minutes). Mlog and notes have different cadences:

- **Water tests (mlog):** Should sync every 6 hours (user manually adds water tests)
- **Notes:** Should sync every 6 hours (user manually adds notes)

Add two new functions:
- `_collect_mlog(tcfg)` — Fetch mlog, write to InfluxDB as `apex_water_tests`
- `_collect_notes(tcfg)` — Fetch notes, write to InfluxDB as `apex_logs`

Add tracking for last full mlog/notes poll time to avoid excessive re-fetches.

### 3.3 InfluxDB Service — Add mlog and notes write/query

**File:** `api/app/services/influx.py`

Add:

```python
# Water tests
MLOG_TYPE_MAP = {1: "KH", 2: "Ca", 4: "Mg", 5: "NO3", 6: "PO4"}
MLOG_UNITS = {"KH": "dkh", "Ca": "ppm", "Mg": "ppm", "NO3": "ppm", "PO4": "ppm"}

def write_water_tests(tenant_id: str, readings: list[dict], bucket_name: str = "") -> int:
    """Write water test results to InfluxDB as apex_water_tests measurement."""

def query_water_tests(tenant_id: str, parameter: str = "", duration: str = "365d") -> list:
    """Query water test results from InfluxDB."""

# Notes
NOTE_TYPES = {0: "Basic", 1: "Good", 2: "Bad", 3: "Ugly", 4: "Maintenance", 5: "Event"}

def write_notes(tenant_id: str, notes: list[dict], bucket_name: str = "") -> int:
    """Write tank notes to InfluxDB as apex_logs measurement."""

def query_notes(tenant_id: str, duration: str = "365d", limit: int = 100) -> list:
    """Query tank notes from InfluxDB."""
```

### 3.4 API Router — Add water tests and notes endpoints

**Option A** (preferred — simpler): Add to existing `/api/telemetry` router

```python
@router.get("/water-tests")
async def get_water_tests(user: dict = Depends(get_current_user)):
    """Get all water test results for this tenant."""

@router.get("/notes")
async def get_notes(user: dict = Depends(get_current_user)):
    """Get tank notes for this tenant."""
```

**Option B** (if we want to keep it separate): New router `api/app/routers/tank_logs.py`

I recommend Option A since these are telemetry-like data.

### 3.5 Frontend — Add Water Tests and Notes pages

**File:** `web/src/App.tsx`

Add routes:

```tsx
<Route path="/water-tests" element={<ProtectedRoute><WaterTestPage /></ProtectedRoute>} />
<Route path="/notes" element={<ProtectedRoute><NotesPage /></ProtectedRoute>} />
```

**New pages needed:**
- `web/src/pages/WaterTestPage.tsx` — Table of water test results (KH, Ca, Mg, NO3, PO4 over time)
- `web/src/pages/NotesPage.tsx` — Chronological timeline of tank notes with type badges

**Navigation:** Add links to sidebar in `DashboardLayout.tsx`

### 3.6 Data Model (Optional — for advanced features)

If we want users to create notes directly in ReefMind-Cloud (not just read-only from Fusion), we need a Postgres model for `TankNote`:

```python
class TankNote(Base):
    __tablename__ = "tank_notes"
    id: UUID primary key
    tenant_id: UUID FK
    note_type: int  # 0-5 matching Fusion types
    title: str
    text: str
    source: str  # "fusion" or "cloud"
    fusion_note_id: str  # for dedup
    created_at: datetime
```

For MVP this is optional — read-only from Fusion is sufficient.

---

## 4. Implementation Order

1. **FusionLiveClient:** Add `get_mlog()` and `get_notes()` methods
2. **InfluxDB service:** Add `write_water_tests()`, `write_notes()`, `query_water_tests()`, `query_notes()`
3. **Collector:** Add mlog and notes sync to background poll cycle
4. **API:** Add `/api/telemetry/water-tests` and `/api/telemetry/notes` endpoints
5. **Frontend:** Add WaterTestPage, NotesPage, navigation links
6. **Testing:** Trixie validates end-to-end

---

## 5. Dependencies

- Fusion credentials must be configured (existing — no change)
- Fusion API endpoints: `/api/apex/{id}/mlog` and `/api/apex/{id}/notes` (no auth changes)
- InfluxDB per-tenant buckets (existing — used for all tenant telemetry)
- No new environment variables required

---

## 6. Risks

- **Large mlog datasets:** 365 days of water tests could be thousands of records. Use InfluxDB atomic delete+write pattern (same as on-prem script).
- **Notes pagination:** The notes API returns paginated results. For MVP, the most recent 200 notes (2 pages at 100 each) is sufficient.
- **Stale data:** Notes and water tests change infrequently (users add them manually). A 6-hour sync cadence is appropriate. No real-time requirement.
- **No local agent:** Unlike the on-prem scripts which ran as cron jobs, the ReefMind-Cloud collector runs in the API process. The existing asyncio lifespan pattern handles this fine.

---

## 7. Success Criteria

1. User configures Fusion credentials via Settings (existing flow)
2. Background collector syncs water tests and notes from Fusion within 6 hours
3. User can view water test results (KH, Ca, Mg, NO3, PO4) with dates and values in a table/chart
4. User can view tank notes with type badges (Good, Bad, Ugly, Maintenance, Event, Basic), titles, and comments
5. Data updates automatically as Fusion data changes
