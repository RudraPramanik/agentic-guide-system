## Why

P4.0–4.4 are done (`protocols`, `travel_rules`, `place_selector`, `day_allocator`, CORS). The next locked batch in `docs/steps/step4.md` is **4.5–4.6**: order a day’s stops for minimum travel with drop-retry (`route_optimizer`), then assign naive wall-clock times with lunch + morning-only enforcement (`schedule_builder`). These pure modules sit between allocation and validation; they must land before 4.7–4.8 so REPLAN can see `dropped_stops` and itineraries carry real `suggested_start_time`.

## What Changes

- **4.5** — Replace stub `src/travel_engine/route_optimizer.py` with `DroppedStop`, `OptimizeResult`, and async `optimize_route` (matrix-once + brute-force permutations ≤720; drop-retry up to `MAX_ROUTE_DROP_ATTEMPTS`; surface `dropped_stops` with reasons; DI via `RoutingProvider`). Add a deterministic `FakeRoutingProvider` under tests for offline proof.
- **4.6** — Replace stub `src/travel_engine/schedule_builder.py` with `ScheduledStop` and `build_day_schedule` (naive `"HH:MM"` clock from `DAY_START_TIME`; lunch gap at `LUNCH_BREAK_START`; morning-only structural categories forced into slots 1–2 with start ≤ `MORNING_SLOT_LATEST_START`; durations via `visit_duration_min`).
- Add focused pytest under `tests/travel_engine/` for optimizer + schedule (★ cases from steps 4.5/4.6 + 4.9 preview); run step ✅ validation snippets.
- Update `docs/context.md` Progress for 4.5–4.6 only (Next step → 4.7); do **not** claim full P4 complete.

**Non-goals:** No edits to `step4.md` / `step4-fix.md` / blueprint; no trip_validator (4.7); no `OsrmRoutingProvider` / tools envelope (4.8); no full P4 pytest plan / smoke / context P4-complete claim (4.9–4.10); no HTTP routers; no SQLAlchemy Place imports; no TSP packages; do not apply stale `openspec/changes/archive/.../p4-travel-engine` tasks that contradict v6.1.

**Source of truth:** Implement from `docs/steps/step4.md` steps 4.5–4.6, aligned with `docs/blueprint_final.md` v6.1 core rules (purity, RoutingProvider DI, Template Method, Configuration-as-data). `docs/steps/step4-fix.md` locks for route ordering + drop-retry are already absorbed into step4’s Decision/Fix Log — consult only if a lock’s *rationale* is unclear.

**AGENT.md constraints that apply:** travel_engine purity (no LLM/network/DB); geo only via `src/geo/` (engine never imports it — routing injected); no new packages without `requirements.txt` + why-comment (explicitly **no** TSP solver).

## Capabilities

### New Capabilities

- `travel-engine-route-optimizer`: Pure async day-route ordering via injected `RoutingProvider`, brute-force permutations, drop-retry with `dropped_stops`.
- `travel-engine-schedule-builder`: Pure wall-clock schedule from ordered stops + consecutive legs (lunch gap, morning-only reordering).

### Modified Capabilities

<!-- Intentionally empty — umbrella `p4-travel-engine-layer` already states these requirements; this change implements them via focused specs. -->

## Impact

- **Code:** `src/travel_engine/route_optimizer.py`, `src/travel_engine/schedule_builder.py` (stubs → real); reads `protocols`, `travel_rules`, `place_selector` types only.
- **AGENT.md / blueprint patterns:** Template Method + DI on optimizer; Configuration-as-data from `travel_rules`; Adapter for OSRM stays in 4.8 (`planner/`), not this batch.
- **Docs:** `docs/context.md` incremental progress only.
- **Tests:** `tests/travel_engine/test_route_optimizer.py`, `tests/travel_engine/test_schedule_builder.py` (+ shared Fake provider helper); step validation snippets; purity still zero geo imports under `travel_engine/`.
- **Build contract:** Exact APIs/behaviors from `docs/steps/step4.md` 4.5–4.6.
