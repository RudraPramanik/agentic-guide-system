## Purpose

OSRM driving-route gateway in `src/geo/`. Returns a `RouteResult` with a named haversine fallback so external OSRM failures never surface as errors to callers.

## Requirements

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

### Requirement: Public estimate route never performs HTTP
The system SHALL provide a public function on `src/geo/osrm.py` (name at implementer’s choice, e.g. `estimate_route`) that, given waypoints `(lat, lng)` with length ≥ 2, returns a `RouteResult` using the same haversine × 1.4 / 30 km/h math as the existing OSRM-miss fallback, with `fallback_used=True` and `encoded_polyline=None`. It MUST NOT call `_call_osrm`, httpx, or `OSRM_BASE_URL`. Fewer than two waypoints MUST raise `ValueError`. `get_route` MUST continue to attempt live OSRM first and MAY reuse this helper on miss.

#### Scenario: Estimate is local and marked fallback
- **WHEN** `estimate_route([(27.04, 88.26), (27.03, 88.27)])` runs with network disabled
- **THEN** a `RouteResult` is returned with `fallback_used=True`, `distance_km > 0`, and `encoded_polyline` empty or `None`

#### Scenario: Fewer than two waypoints rejected
- **WHEN** `estimate_route` is called with fewer than two waypoints
- **THEN** a `ValueError` is raised

#### Scenario: get_route still tries live OSRM first
- **WHEN** `get_route` is called with a reachable `OSRM_BASE_URL`
- **THEN** the live `/route/v1/driving` path is still attempted before any estimate fallback
