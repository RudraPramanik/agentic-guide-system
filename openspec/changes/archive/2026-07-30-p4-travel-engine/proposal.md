## Why

P3 delivered enrichment + Qdrant indexing; the next layer is the pure-Python travel intelligence that scores places, allocates days, optimizes routes, builds schedules, and validates itineraries — without LLM or I/O. Before coding, a pre-flight review (`docs/blueprint.md`) found a real vocabulary bug in the v6 `travel_rules.py` draft (structural `Place.category` conflated with interest `enriched_tags`) plus underspecified route ordering and drop-retry coordination. Locking those fixes into P4 now prevents KeyErrors, dead config, and silent wrong durations once P5 tools wrap this layer.

## What Changes

- Implement **P4 Travel Engine** (blueprint steps **4.0–4.8**) as pure Python under `src/travel_engine/` + thin planner DI stub + CORS.
- **Follow `docs/blueprint_final.md` v6.1** as Planner SoT (pre-flight locks merged; former `docs/blueprint.md` is a pointer only):
  - Split structural vs interest vocabularies; complete `VISIT_DURATION_BY_CATEGORY` for all P2 categories (incl. `attraction`, `trailhead`); remove dead `sunrise_point`; drop interest-only keys (`trek`, `cultural`) from duration maps.
  - Lock place scoring as **sum** of matching interest weights.
  - Lock route ordering as brute-force permutation TSP (≤720 perms at `MAX_PLACES_PER_DAY=6`); no TSP library.
  - Surface `dropped_stops` from PLAN-phase drop-retry for later REPLAN coordination.
  - Route `explain_selection` into trace-shaped data (not a new `TripEvaluation` column).
- Add **CORS middleware** (step 4.0) in `create_app()` with `CORS_ALLOWED_ORIGINS` from settings.
- Author `docs/steps/step4.md` as the Cursor build prompt from blueprint_final v6.1.
- Record cookie SameSite Option A in `docs/context.md` (docs-only if already present).
- Forward-lock notes for P5/P6 remain in blueprint_final — **not implemented in P4** beyond data shapes (`dropped_stops`, explain strings).

## Capabilities

### New Capabilities

- `travel-engine`: Pure-Python protocols, rules, place selection, day allocation, route optimization, schedule building, trip validation — no LLM/geo/DB I/O; injectable `RoutingProvider`.
- `planner-routing-stub`: `OsrmRoutingProvider` wrapping `geo/osrm.py` + minimal `execute_tool` / `ToolResult` skeleton for P5 to fill.
- `cors-middleware`: FastAPI `CORSMiddleware` with credentialed explicit origins from settings.

### Modified Capabilities

<!-- Intentionally empty: no archived main-spec requirements change for travel_engine (new). -->

## Impact

- **Code:** `src/travel_engine/*` (today stub/empty), `src/planner/routing_provider.py`, thin `src/planner/tools/` stub, `src/main.py` + `src/config.py` for CORS.
- **AGENT.md:** travel_engine remains pure (no LLM/network/DB); routing times injected via `RoutingProvider`; geo only via `src/geo/` (provider wraps it outside travel_engine).
- **Docs:** `docs/steps/step4.md` becomes P4 implementation prompt; `docs/context.md` updated after validated steps; **`docs/blueprint_final.md` v6.1 is Planner SoT** (pre-flight merged).
- **Tests:** unit tests with `FakeRoutingProvider` — no network; pytest expands beyond current 92.
- **Non-goals:** no LangGraph, no planner SSE, no trip CRUD, no REPLAN tools, no Redis, no SameSite cookie code change (decision only), no P5/P6 D.* implementations beyond data shapes P4 must emit (`dropped_stops`, explain strings for trace).
