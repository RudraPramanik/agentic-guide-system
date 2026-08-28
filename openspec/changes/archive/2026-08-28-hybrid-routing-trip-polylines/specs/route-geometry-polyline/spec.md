## ADDED Requirements

### Requirement: Hybrid generate path can persist road polylines
When the injected `RoutingProvider` returns non-`None` values from `route_polyline` (e.g. hybrid or full OSRM backend), `optimize_route` / `populate_leg_polylines` and downstream schedule persistence MUST continue to map those strings onto stop `leg_polyline` / `TripPlace.polyline` without requiring a second OSRM pass in `build_geojson`. GeoJSON MUST emit LineString features when persisted polylines decode, and MUST remain Point-only when all polylines are null — no invented coordinates.

#### Scenario: Hybrid geometry reaches GeoJSON LineStrings
- **WHEN** a trip is saved from a schedule whose stops include non-null `leg_polyline` values produced under a hybrid routing backend
- **THEN** `GET` trip GeoJSON includes at least one LineString feature for that day (when decode succeeds) in addition to Point features

#### Scenario: Soft-fail geometry still Point-only
- **WHEN** every `route_polyline` call returns `None` under hybrid or haversine
- **THEN** saved trip GeoJSON remains a valid FeatureCollection of Points with no LineString for that day and no 500
