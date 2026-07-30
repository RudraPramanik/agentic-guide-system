## Why

P4.0–4.6 are done (CORS, protocols, rules, selector, allocator, route_optimizer, schedule_builder). The next locked batch in `docs/steps/step4.md` is **4.7–4.8**: chain-of-responsibility itinerary validation (`trip_validator`), then the planner-side OSRM adapter (`OsrmRoutingProvider`) plus a minimal `ToolResult` / `execute_tool` envelope so P5 can grow tools without inventing a parallel tree. Validation must land before the adapter so smoke/pytest can assert a full select→allocate→optimize→schedule→validate path; the adapter is the only P4 module allowed to import `src.geo`.

## What Changes

- **4.7** — Replace stub `src/travel_engine/trip_validator.py` with `ValidationResult`, `DayPlan`, `TripItinerary`, per-rule check functions, and `validate_trip` (daily travel cap, no repeated places, morning slots, anchor per day, geo coherence). Observe `dropped_stops` as a **warning** hint for P5 REPLAN (prefer expand_poi_search), not an error. Empty itinerary → `passed=False`, `errors=["empty_itinerary"]`.
- **4.8** — Replace stub `src/planner/routing_provider.py` with `OsrmRoutingProvider` wrapping `geo/osrm.get_route` (full directed pairwise legs; map `fallback_used` → `RouteLeg.used_fallback`). Extend stub `src/planner/tools/schemas.py` with `ToolResult` and stub `src/planner/tools/registry.py` with `execute_tool` skeleton (unknown tool → `ok=False`, never raise). Full 12-tool registry / PHASE_TOOLS is **P5 — out of scope**.
- Add focused pytest: `tests/travel_engine/test_trip_validator.py`, `tests/planner/test_routing_provider.py`, `tests/planner/test_execute_tool_stub.py` (★ cases from steps 4.7/4.8 + 4.9 preview).
- Update `docs/context.md` Progress for 4.7–4.8 only (Next step → 4.9); do **not** claim full P4 complete.

**Non-goals:** No full P4 pytest plan / purity AST suite / smoke / context P4-complete claim (4.9–4.10); no LangGraph, SSE, or real tool bodies; no `TravelState.used_osrm_fallback` (P5 — P4 only sets `RouteLeg.used_fallback`); no HTTP routers; no SQLAlchemy Place imports; no edits to blueprint / step4.md unless a lock conflict appears.

**Source of truth:** Implement from `docs/steps/step4.md` steps 4.7–4.8, aligned with `docs/blueprint_final.md` v6.1. Where blueprint §4.8 mentions setting `state.used_osrm_fallback`, follow step4’s locked adapter contract for P4 (`RouteLeg.used_fallback` only).

**AGENT.md constraints that apply:** travel_engine purity (no LLM/network/DB; no `src.geo`); geo only via `src/geo/` (adapter is the sole P4 importer of `osrm`); no new packages without `requirements.txt` + why-comment; tool failures return envelopes, never uncaught exceptions to callers.

## Capabilities

### New Capabilities

- `travel-engine-trip-validator`: Pure chain-of-responsibility validation over a day-plan itinerary; returns `ValidationResult` with errors/warnings (never raises on merely-invalid plans).
- `planner-routing-provider`: Adapter implementing `RoutingProvider` via `geo/osrm.get_route`; maps fallback flag onto `RouteLeg`.
- `planner-tools-envelope`: Minimal `ToolResult` + `execute_tool` skeleton (unknown tool → `ok=False`).

### Modified Capabilities

<!-- Intentionally empty — no existing main-spec requirement deltas; prior P4 batches already shipped focused capability specs. -->

## Impact

- **Code:** `src/travel_engine/trip_validator.py` (stub → real); `src/planner/routing_provider.py`, `src/planner/tools/schemas.py`, `src/planner/tools/registry.py` (stubs → thin real).
- **Reads:** `schedule_builder.ScheduledStop`, `route_optimizer.DroppedStop`, `travel_rules` constants (`MAX_DAILY_TRAVEL_MIN`, `MORNING_*`, `ANCHOR_MIN_SCORE`, `GEO_COHERENCE_MAX_STDDEV_KM`), `protocols.RouteLeg` / `RoutingProvider`, `geo/osrm.get_route`.
- **Docs:** `docs/context.md` incremental progress only; stubs list: remove `trip_validator` stub note; keep planner graph / tool *bodies* as stubs.
- **Tests:** validator + provider + execute_tool stub tests; travel_engine purity still zero geo imports after 4.8.
- **Build contract:** Exact APIs/behaviors from `docs/steps/step4.md` 4.7–4.8.
