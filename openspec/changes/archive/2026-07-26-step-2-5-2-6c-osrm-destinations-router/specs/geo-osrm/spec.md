## ADDED Requirements

### Requirement: OSRM route gateway with haversine fallback

The system SHALL provide `src/geo/osrm.py` with public `get_route(waypoints: list[tuple[float, float]]) -> RouteResult`. Waypoints MUST be `(lat, lng)` pairs with length ≥ 2 (otherwise `ValueError`). The gateway MUST call OSRM at `{OSRM_BASE_URL}/route/v1/driving/...` using `lng,lat` URL order, explicit httpx timeouts, and tenacity retry (2 attempts on TimeoutException/ConnectError only). On OSRM failure, empty routes, or unusable response, the system MUST return `_fallback_route` (haversine legs × 1.4, duration from average speed 30 km/h, `fallback_used=True`) and MUST NOT raise httpx errors to callers. Successful OSRM responses MUST map distance meters→km, duration seconds→minutes, and geometry→`encoded_polyline`.

#### Scenario: Live route returns positive distance

- **WHEN** `get_route([(27.04, 88.26), (27.03, 88.27)])` runs with network available
- **THEN** `distance_km > 0` and a `RouteResult` is returned (OSRM or fallback)

#### Scenario: OSRM miss uses haversine fallback

- **WHEN** `_call_osrm` returns `None`
- **THEN** `get_route` returns `fallback_used=True` and `distance_km > 0`

#### Scenario: Fewer than two waypoints rejected

- **WHEN** `get_route` is called with fewer than two waypoints
- **THEN** a `ValueError` is raised
