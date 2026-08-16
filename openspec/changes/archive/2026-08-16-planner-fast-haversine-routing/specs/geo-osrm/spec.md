## ADDED Requirements

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
