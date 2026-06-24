# ReefMind-Cloud Design Fixes (v2)

This document details the design fixes for critical issues identified in the ReefMind-Cloud project.

## Issue 1: Dashboard Time Buttons

### Diagnosis
- `DashboardPage.tsx` useEffects for charts and overview are missing `duration` in dependency arrays.
- String-based conversion (`replace('d', '24')`) is mathematically incorrect for '30d' and similar values.

### Proposed Fixes
1.  **Dependency Arrays**: Update `useEffect` hooks in `DashboardPage.tsx` to include `duration`.
2.  **Conversion Helper**: Implement a utility function:
    ```typescript
    const getHoursFromDuration = (duration: string): number => {
      if (duration.endsWith('h')) return parseInt(duration);
      if (duration.endsWith('d')) return parseInt(duration) * 24;
      return 24; // Default
    };
    ```
3.  **UI Updates**: Update the button array in `DashboardPage.tsx` to: `['1h', '6h', '24h', '30d', '60d', '90d']`.

---

## Issue 2: Historical Backfill

### Diagnosis
- The Fusion API enforces a ~7-day limit. Requests for 30/60/90 days return 400 Bad Request.
- `collector.py` marks `backfill_complete` as true regardless of whether data was actually written.

### Proposed Fixes
1.  **Backend Logic (`collector.py`)**:
    - Cap API call: `requests.get(..., params={"days": min(backfill_days, 7)})`.
    - Flag Update: Only set `backfill_complete = True` inside the telemetry write success block.
2.  **Settings UI (`SettingsPage.tsx`)**:
    - Update dropdown to reflect the 7-day constraint or document clearly that values > 7 days will accumulate over time via live polling.
    - Add a warning: "Note: Initial backfill is capped at 7 days due to API limitations. Remaining data will be filled incrementally."

---

## Issue 3: Regression Test Suite

### Strategy
Implement integration tests covering these identified failure points:

| Test Scenario | Validation Logic |
| :--- | :--- |
| **Duration Switch** | Mock data fetch; verify `useEffect` re-triggers when `duration` state changes. |
| **Duration Parsing** | Unit test `getHoursFromDuration` with '30d' -> 720, '6h' -> 6. |
| **Route Integrity** | Validate `/water-tests` and `/notes` are rendered before catch-all `/` route. |
| **Backfill API** | Mock 400 response for >7 days; verify system handles gracefully without marking complete. |
| **Backfill Logic** | Ensure `backfill_complete` is `false` if `write_telemetry` returns 0 points. |
| **Note Dedup** | Feed mixed input (`_id`, `id`) and verify normalized ID structure. |
| **Build Integrity** | Run minification build; assert presence of new constant strings in artifact. |
