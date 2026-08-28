## MODIFIED Requirements

### Requirement: Settings select routing backend
The system SHALL expose `get_settings().ROUTING_BACKEND` as one of `haversine`, `osrm`, or `hybrid` (default `haversine` unless operators document a different default). Unknown values MUST be treated as `haversine` (fail-soft, never raise at request time). Access MUST go through `get_settings()` only.

#### Scenario: Default backend is haversine
- **WHEN** `ROUTING_BACKEND` is unset
- **THEN** `get_settings().ROUTING_BACKEND` is `haversine`

#### Scenario: osrm backend is selectable
- **WHEN** `ROUTING_BACKEND` is `osrm`
- **THEN** `get_settings().ROUTING_BACKEND` is `osrm`

#### Scenario: hybrid backend is selectable
- **WHEN** `ROUTING_BACKEND` is `hybrid`
- **THEN** `get_settings().ROUTING_BACKEND` is `hybrid`

### Requirement: get_routing_provider selects the production adapter
`src/planner/routing_provider.py` SHALL export `get_routing_provider()` that returns `HaversineRoutingProvider` when `ROUTING_BACKEND` is `haversine` (or unknown), `OsrmRoutingProvider` when `ROUTING_BACKEND` is `osrm`, and the hybrid adapter when `ROUTING_BACKEND` is `hybrid`. Callers that need a live matrix MUST go through this factory unless a test injects a Fake. `travel_engine` MUST still have zero geo imports.

#### Scenario: Default factory is haversine
- **WHEN** `get_routing_provider()` runs with default settings
- **THEN** the returned adapter’s `travel_matrix` does not invoke `get_route`

#### Scenario: osrm factory returns the OSRM adapter
- **WHEN** `ROUTING_BACKEND` is `osrm` and `get_routing_provider()` runs
- **THEN** the returned adapter is `OsrmRoutingProvider`

#### Scenario: hybrid factory returns the hybrid adapter
- **WHEN** `ROUTING_BACKEND` is `hybrid` and `get_routing_provider()` runs
- **THEN** the returned adapter’s `travel_matrix` does not invoke `get_route` and its `route_polyline` may invoke the geo route helper for geometry
