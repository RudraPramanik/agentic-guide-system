## Purpose

Planner-side routing adapters implementing `RoutingProvider` (P4 step 4.8 + haversine factory). Keeps geo I/O outside `travel_engine`.

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

### Requirement: OsrmRoutingProvider.route_polyline wraps get_route fail-soft
`OsrmRoutingProvider` MUST implement `route_polyline(waypoints: list[tuple[float, float]]) -> str | None` by calling existing `src.geo.osrm.get_route(waypoints)` with no new OSRM endpoint type and no change to `get_route`'s public signature.

Return rules:

- If `fallback_used` is true → `None`
- If `encoded_polyline` is missing/empty → `None`
- Otherwise → the encoded polyline string
- On any exception from `get_route` (including `ValueError` for fewer than 2 waypoints) → catch and return `None` (never raise to `optimize_route`)

#### Scenario: Non-fallback geometry returned
- **WHEN** `get_route` returns `fallback_used=False` with a non-empty `encoded_polyline`
- **THEN** `route_polyline` returns that string

#### Scenario: Fallback maps to None
- **WHEN** `get_route` returns `fallback_used=True`
- **THEN** `route_polyline` returns `None`

#### Scenario: Exceptions map to None
- **WHEN** `get_route` raises
- **THEN** `route_polyline` returns `None` and does not propagate

### Requirement: Settings select routing backend
The system SHALL expose `get_settings().ROUTING_BACKEND` as one of `haversine` or `osrm` (default `haversine`). Unknown values MUST be treated as `haversine` (fail-soft, never raise at request time). Access MUST go through `get_settings()` only.

#### Scenario: Default backend is haversine
- **WHEN** `ROUTING_BACKEND` is unset
- **THEN** `get_settings().ROUTING_BACKEND` is `haversine`

#### Scenario: osrm backend is selectable
- **WHEN** `ROUTING_BACKEND` is `osrm`
- **THEN** `get_settings().ROUTING_BACKEND` is `osrm`

### Requirement: HaversineRoutingProvider never calls OSRM HTTP
The project SHALL provide `HaversineRoutingProvider` in `src/planner/routing_provider.py` implementing `RoutingProvider`. `travel_matrix` MUST build the full directed i≠j `RouteLeg` set using the public geo estimate helper (haversine × 1.4, 30 km/h), with `used_fallback=True` on every leg. It MUST NOT call `get_route` or any httpx/OSRM URL. Zero or one waypoints MUST return an empty list. `route_polyline` MUST return `None` and MUST NOT raise.

#### Scenario: Three waypoints yield six fallback legs
- **WHEN** `travel_matrix` is called with three waypoints
- **THEN** the result contains exactly six directed legs, each with `used_fallback=True` and `distance_km > 0`, and no HTTP client is used

#### Scenario: Polyline is always absent
- **WHEN** `route_polyline` is called with two or more waypoints
- **THEN** the return value is `None`

#### Scenario: Single waypoint yields no legs
- **WHEN** `travel_matrix` is called with one waypoint
- **THEN** the result is an empty list

### Requirement: get_routing_provider selects the production adapter
`src/planner/routing_provider.py` SHALL export `get_routing_provider()` that returns `HaversineRoutingProvider` when `ROUTING_BACKEND` is `haversine` (or unknown) and `OsrmRoutingProvider` when `ROUTING_BACKEND` is `osrm`. Callers that need a live matrix MUST go through this factory unless a test injects a Fake. `travel_engine` MUST still have zero geo imports.

#### Scenario: Default factory is haversine
- **WHEN** `get_routing_provider()` runs with default settings
- **THEN** the returned adapter’s `travel_matrix` does not invoke `get_route`

#### Scenario: osrm factory returns the OSRM adapter
- **WHEN** `ROUTING_BACKEND` is `osrm` and `get_routing_provider()` runs
- **THEN** the returned adapter is `OsrmRoutingProvider`
