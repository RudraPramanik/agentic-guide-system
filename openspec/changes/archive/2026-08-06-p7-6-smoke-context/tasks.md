## 1. Setup

- [x] 1.1 Read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.6 before coding
- [x] 1.2 Confirm P7.0–7.5 are ✅ in `docs/context.md` and `scripts/test_p7_smoke.py` is absent (or note existing draft)

## 2. Import guards

- [x] 2.1 Spot-check trips edit modules (`src/trips/service.py`, `router.py`, `dependencies.py`, related edit helpers) for forbidden imports: `litellm`, `langgraph`, `PlannerService`, `execute_tool`, `redis`
- [x] 2.2 Fix any accidental forbidden imports with minimal delta (must not change edit semantics); re-scan until clean

## 3. Optional smoke script

- [x] 3.1 Decide: write `scripts/test_p7_smoke.py` (preferred) or intentionally omit (document in apply notes)
- [x] 3.2 If writing smoke: owned trip; reorder day 1; assert exactly one `TripEditEvent`; GeoJSON polyline/LineString when polylines present; import-guard section; offline Fake default; live OSRM behind env flag; fail-fast non-zero exit
- [x] 3.3 If smoke written: run `python scripts/test_p7_smoke.py` → green

## 4. Pytest verification

- [x] 4.1 Run `python -m pytest tests/trips/test_edit_replan.py -v` → green
- [x] 4.2 Run `python -m pytest tests/ -v` → green
- [x] 4.3 If pytest fails: fix minimal regression under existing P7 locks; do **not** update `docs/context.md` until green

## 5. Context checkpoint (only after green)

- [x] 5.1 Update `docs/context.md`: Last updated = today; Phase P7 complete; Next → post-P7 / production readiness; Progress 7.0–7.6 ✅; Current state (day edit/replan HTTP + TripEditEvent; shared polyline helper; preserve-order reorder)
- [x] 5.2 Confirm Implemented modules cover edit methods, routes, `rate_limit_trip_edit`, `mark_trip_edited`, `populate_leg_polylines`, preserve-order schedule; Live endpoints include four edit rows; Known MVP limitation: concurrent edits last-write-wins
- [x] 5.3 Stubs: remove “P7 trip edit/replan HTTP still stubs”; keep evaluation HTTP stub; do **not** claim evaluation HTTP done; do **not** start F1 or mark roadmap production items done
- [x] 5.4 If smoke was added, list `scripts/test_p7_smoke.py` under Scripts in context.md
