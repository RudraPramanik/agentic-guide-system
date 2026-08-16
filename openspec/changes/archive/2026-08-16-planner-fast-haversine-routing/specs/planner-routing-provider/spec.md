## ADDED Requirements

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
