## ADDED Requirements

### Requirement: OsrmRoutingProvider.route_polyline wraps get_route fail-soft
`OsrmRoutingProvider` MUST implement `route_polyline(waypoints: list[tuple[float, float]]) -> str | None` by calling existing `src.geo.osrm.get_route(waypoints)` with no new OSRM endpoint type and no change to `get_route`'s public signature.

Return rules:

- If `fallback_used` is true → `None`
- If `encoded_polyline` is missing/empty → `None`
- Otherwise → the encoded polyline string
- On any exception from `get_route` (including `ValueError` for &lt;2 waypoints) → catch and return `None` (never raise to `optimize_route`)

#### Scenario: Non-fallback geometry returned
- **WHEN** `get_route` returns `fallback_used=False` with a non-empty `encoded_polyline`
- **THEN** `route_polyline` returns that string

#### Scenario: Fallback maps to None
- **WHEN** `get_route` returns `fallback_used=True`
- **THEN** `route_polyline` returns `None`

#### Scenario: Exceptions map to None
- **WHEN** `get_route` raises
- **THEN** `route_polyline` returns `None` and does not propagate
