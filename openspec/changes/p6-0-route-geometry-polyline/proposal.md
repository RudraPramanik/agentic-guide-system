## Why

P4/P5 compute travel **time/distance** via `travel_matrix` but never produce road geometry. P6 persistence (`TripPlace.polyline`) and `GET /trips/{id}/geojson` LineStrings depend on that geometry existing in `TravelState.schedule`. Step **6.0** in `docs/steps/step6.md` (blueprint SoT: `docs/blueprint_final.md` v6.1) closes this gap surgically before trips HTTP / SSE land.

## What Changes

- Add `RoutingProvider.route_polyline(waypoints) -> str | None` (fail-soft; never raises).
- Implement on `OsrmRoutingProvider` as a thin wrapper over existing `geo.osrm.get_route` (no new OSRM call type / no signature change to `get_route`).
- After the winning stop order is chosen, `optimize_route` populates `OptimizeResult.leg_polylines` + `day_polyline` with at most `len(ordered)+1` geometry calls (not during permutation search).
- Update shared `FakeRoutingProvider` (+ smoke fakes) so Protocol consumers keep working.
- **BREAKING (in-graph schedule shape):** normalize `TravelState.schedule` from today's `list[list[stop]]` to the locked **per-day dict** shape in step 6.0 (`day`, `stops[]` with `leg_polyline`, `day_polyline`, travel totals). Update `build_route` / `build_schedule` to carry polylines, and adapt consumers that assume list-of-lists (`validate_itinerary`, narrative helpers, planner tests).
- Document the schedule shape on `TravelState` (comment / typed contract).
- Out of this change: `TripService.save_from_state`, trips CRUD, GeoJSON HTTP, planner SSE, Redis/cache (6.1–6.5).

## Capabilities

### New Capabilities

- _(none — main capability `route-geometry-polyline` already exists from `harden-p6-planner-api-v2`; this change implements the 6.0 slice)_

### Modified Capabilities

- `route-geometry-polyline`: Pin 6.0 implementation requirements (Protocol, optimizer, schedule threading); clarify that Trip persist / GeoJSON HTTP remain deferred to 6.1/6.3 while schedule must already carry polyline fields.
- `travel-engine-protocols`: Add `route_polyline` to `RoutingProvider`.
- `travel-engine-route-optimizer`: Add `leg_polylines` / `day_polyline` on `OptimizeResult` and post-order geometry population rules.
- `planner-routing-provider`: `OsrmRoutingProvider.route_polyline` fail-soft adapter behavior.
- `planner-travel-state`: Lock `schedule` as list of day dicts (step 6.0 shape).
- `planner-plan-replan-tools`: `build_route` / `build_schedule` must emit day-dict schedule with polylines; `validate_itinerary` must accept that shape.

## Impact

- **Code:** `src/travel_engine/protocols.py`, `route_optimizer.py`; `src/planner/routing_provider.py`; `src/planner/tools/build_route.py`, `build_schedule.py`, `validate_itinerary.py`; `src/planner/graph/state.py`; possibly `write_narrative.py` helpers; `tests/travel_engine/fake_routing.py`; planner/travel_engine tests; `scripts/test_p4_smoke.py` fake if it implements `RoutingProvider`.
- **APIs:** None (no new HTTP). Prepares state for 6.1+ persistence.
- **Deps:** No new packages.
- **AGENT.md:** `travel_engine` stays pure (Protocol DI only); geo only via `src/geo/` inside the planner adapter; no litellm changes.
- **Non-goals:** trips repo/service/router; SSE generate; Redis; changing `geo/osrm.get_route` contract; computing geometry inside the permutation loop; P7 edit/reoptimize HTTP.
