## 1. Step 4.7 — trip_validator

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, `docs/steps/step4.md` step 4.7, and design D2–D5 before coding
- [x] 1.2 Implement `ValidationResult`, `DayPlan`, `TripItinerary` in `src/travel_engine/trip_validator.py` (reuse `ScheduledStop`, `DroppedStop`)
- [x] 1.3 Implement check functions: `check_daily_travel_cap`, `check_no_repeat_places`, `check_morning_slots`, `check_anchor_per_day`, `check_geo_coherence` (threshold from `GEO_COHERENCE_MAX_STDDEV_KM`; no magic number; skip geo if <2 stops)
- [x] 1.4 Implement `validate_trip`: empty days → `passed=False`, `errors=["empty_itinerary"]`; run fixed check chain; add dropped_stops warning token when any day has drops; never raise on merely-invalid plans; no `src.geo`
- [x] 1.5 Run step 4.7 ✅ validation snippet from `docs/steps/step4.md`
- [x] 1.6 Confirm no `src.geo` / httpx / litellm / qdrant / sqlalchemy imports in `trip_validator.py`

## 2. Step 4.7 — validator tests

- [x] 2.1 Create `tests/travel_engine/test_trip_validator.py`
- [x] 2.2 Cover: good fixture → `errors=[]`, `passed=True`
- [x] 2.3 Cover: empty itinerary → `errors` contains `empty_itinerary`; repeat place → distinct error; late morning-only viewpoint → distinct error
- [x] 2.4 Cover: day without anchor (`score <= ANCHOR_MIN_SCORE`) → error; geo std-dev over threshold → error
- [x] 2.5 Cover: non-empty `dropped_stops` on an otherwise-valid plan → warning token, still `passed=True`
- [x] 2.6 Run `python -m pytest tests/travel_engine/test_trip_validator.py -v`

## 3. Step 4.8 — OsrmRoutingProvider

- [x] 3.1 Re-read `docs/steps/step4.md` step 4.8 and design D6 before coding
- [x] 3.2 Implement `OsrmRoutingProvider.travel_matrix` in `src/planner/routing_provider.py`: full directed pairwise `get_route` calls; map `fallback_used` → `RouteLeg.used_fallback`; `duration_min=round(...)`; empty/single waypoint → `[]`; never re-raise httpx for route miss
- [x] 3.3 Confirm this is the only new P4 geo importer; do **not** set `TravelState.used_osrm_fallback`
- [x] 3.4 Create `tests/planner/test_routing_provider.py` with mocked `get_route`: pairwise leg count; fallback flag mapping; single waypoint → `[]`
- [x] 3.5 Run `python -m pytest tests/planner/test_routing_provider.py -v`

## 4. Step 4.8 — tools envelope stub

- [x] 4.1 Implement `ToolResult` in `src/planner/tools/schemas.py` (`ok`, `code`, `message`, `data`)
- [x] 4.2 Implement `execute_tool` skeleton in `src/planner/tools/registry.py`: unknown name → `ToolResult(ok=False, code="unknown_tool", ...)`; never raise; no PHASE_TOOLS / tool bodies
- [x] 4.3 Run step 4.8 ✅ validation snippet from `docs/steps/step4.md`
- [x] 4.4 Create `tests/planner/test_execute_tool_stub.py` covering unknown tool soft failure
- [x] 4.5 Run `python -m pytest tests/planner/test_execute_tool_stub.py -v`

## 5. Closeout

- [x] 5.1 Run `python -m pytest tests/travel_engine/ tests/planner/test_routing_provider.py tests/planner/test_execute_tool_stub.py -v` (or full `tests/`) — no regressions
- [x] 5.2 PowerShell purity scan under `src/travel_engine` for `src.geo|httpx|litellm|qdrant|sqlalchemy` — zero matches
- [x] 5.3 Update `docs/context.md`: Progress 4.7–4.8 ✅, Implemented modules for trip_validator + OsrmRoutingProvider + ToolResult/execute_tool stub, Stubs list trimmed (`trip_validator` no longer stub), Next step → 4.9; do not mark full P4 done
