## Purpose

Planner-side OSRM adapter implementing `RoutingProvider` (P4 step 4.8). Keeps geo I/O outside `travel_engine`.

## Requirements

### Requirement: OsrmRoutingProvider adapts geo/osrm to RoutingProvider
The project SHALL provide `src/planner/routing_provider.py` with class `OsrmRoutingProvider` that implements `RoutingProvider.travel_matrix` by wrapping `src.geo.osrm.get_route`, as locked in `docs/steps/step4.md` step 4.8 and `docs/blueprint_final.md` v6.1.

For every ordered pair of waypoints `(i, j)` with `i != j`, the provider MUST call `get_route([(lat_i, lng_i), (lat_j, lng_j)])` and produce a `RouteLeg` with:
- `from_place_id` / `to_place_id` from the waypoint ids
- `duration_min` = `round(result.duration_min)`
- `distance_km` = `result.distance_km`
- `used_fallback` = `result.fallback_used`

Those pairwise calls MUST run with **bounded concurrency** (see capability `osrm-travel-matrix-concurrency`) rather than a purely serial nested await loop, while still returning the complete directed leg set. Zero or one waypoints MUST return an empty leg list. The provider MUST NOT re-raise httpx failures for route miss (`get_route` already applies the named haversine fallback). This module MAY import `src.geo.osrm`; modules under `src/travel_engine/` MUST still have zero geo imports after this step.

P4 MUST NOT set LangGraph / `TravelState.used_osrm_fallback` — fallback visibility for P4 is `RouteLeg.used_fallback` only.

#### Scenario: Pairwise matrix from mocked get_route
- **WHEN** `travel_matrix` is called with three waypoints and `get_route` is mocked to return fixed `RouteResult` values
- **THEN** the result contains exactly six directed legs (all i≠j pairs) and no uncaught httpx exception reaches the caller

#### Scenario: Fallback flag maps onto RouteLeg
- **WHEN** the underlying `get_route` returns `fallback_used=True`
- **THEN** the corresponding `RouteLeg.used_fallback` values are true

#### Scenario: Single waypoint yields no legs
- **WHEN** `travel_matrix` is called with one waypoint
- **THEN** the result is an empty list

#### Scenario: Multi-pair matrix is not strictly serial
- **WHEN** `travel_matrix` runs with four waypoints under an instrumented slow `get_route`
- **THEN** completion wall time is materially faster than a strictly serial nested-loop baseline for the same delay, subject to the configured concurrency cap
