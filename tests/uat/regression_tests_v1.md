# Regression Test Plan v1

This document outlines the regression test suite for ReefMind Cloud.
Run these before and after any code deployment to catch regressions immediately.

## Test Scenarios

| ID | Name | What to Check | How to Verify (Command) | Expected Result | Why It Regressed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | Duration buttons re-fetch | Dashboard data fetching | `grep -n 'duration' web/src/pages/DashboardPage.tsx` | Line 181 has `[activeTab, dataSource, duration]` | Inconsistent dependency arrays caused stale data. |
| **02** | Overview preload re-fetches | Overview component dependency | `grep -n 'overview' web/src/pages/DashboardPage.tsx` | Line 194 has `[summary, dataSource, duration]` | Race conditions in component mounting. |
| **03** | Days-to-hours conversion | Data formatting helper | `grep -n 'getHoursFromDuration' web/src/pages/DashboardPage.tsx` | Line 45 has `getHoursFromDuration` function | Incorrect unit conversion logic. |
| **04** | Duration buttons range | UI button options | `grep -n '30d\|60d\|90d' web/src/pages/DashboardPage.tsx` | Line 292 has `['1h', '6h', '24h', '30d', '60d', '90d']` | Missing configuration for long-term views. |
| **05** | Backfill API cap | API input validation | `grep -n 'capped_days' api/app/services/collector.py` | Line 301 has `capped_days = min(backfill_days, 7)` | Uncapped backfills overwhelmed the Fusion API. |
| **06** | Backfill complete block | Indentation/logic flow | `sed -n '330,356p' api/app/services/collector.py` | `_mark_backfill()` is inside `if backfill_points:` block | Logic executed outside of success flow. |
| **07** | Route ordering | API route precedence | `grep -n '@router.get' api/app/routers/telemetry.py` | Static routes (water-tests, notes, controller) before `/{probe_name}` | Wildcard swallowed static paths. |
| **08** | Notes dedup fallback | Multi-field ID resolution | `grep -n 'raw_id' api/app/services/influx.py` | Line 288 has fallback: `id` → `note_id` → `_id` → `ID` | Schema changes broke identifier detection. |
| **09** | No --reload flag | Production Docker safety | `grep reload api/Dockerfile` | Should return empty (no output) | Dev flag left in production image. |
| **10** | Port mapping | Container networking | `docker ps --filter name=reefmind-web --format '{{.Ports}}'` | Output shows `8080->80` | Port mapping mismatch after rebuild. |
| **11** | API health | Container communication | `docker exec reefmind-postgres wget -qO- http://reefmind-api:8000/api/health` | `status":"ok"` | Network bridge misconfiguration. |
| **12** | Bundle duration strings | Frontend asset build | `docker run --rm reefmind-web:latest grep -cE '(30d|60d|90d)' /usr/share/nginx/html/assets/index-*.js` | >= 1 | Assets not rebuilding during CI pipeline. |

## How to Use

```bash
# Run all grep-based checks from repo root
cd /opt/data/projects/reefmind/cloud

echo "=== TEST 01 ===" && grep -n 'duration' web/src/pages/DashboardPage.tsx | grep -E '181|194'
echo "=== TEST 03 ===" && grep -n 'getHoursFromDuration' web/src/pages/DashboardPage.tsx
echo "=== TEST 04 ===" && grep -n '30d\|60d\|90d' web/src/pages/DashboardPage.tsx
echo "=== TEST 05 ===" && grep -n 'capped_days' api/app/services/collector.py
echo "=== TEST 06 ===" && sed -n '332,352p' api/app/services/collector.py | head -5
echo "=== TEST 07 ===" && grep -n '@router.get' api/app/routers/telemetry.py
echo "=== TEST 08 ===" && grep -n 'raw_id' api/app/services/influx.py
echo "=== TEST 09 ===" && grep reload api/Dockerfile; echo "Exit: $?"

# Run docker-based checks
echo "=== TEST 10 ===" && docker ps --filter name=reefmind-web --format '{{.Ports}}'
echo "=== TEST 11 ===" && docker exec reefmind-postgres wget -qO- http://reefmind-api:8000/api/health
echo "=== TEST 12 ===" && docker run --rm reefmind-web:latest grep -cE '(30d|60d|90d)' /usr/share/nginx/html/assets/index-*.js 2>/dev/null
```

## History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-06-24 | Initial suite — covers duration deps, backfill cap, route order, notes dedup, deploy sanity |

## Related Documents

- `sprint_plan.md` — Sprint-level UAT plan
- `api_contract_tests.md` — API contract/version tests
- `smoke_suite.md` — Quick smoke test for basic functionality
