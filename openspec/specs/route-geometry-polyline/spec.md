## Purpose

Route geometry for planner itineraries — `RoutingProvider.route_polyline`, optimizer threading into schedule stops, persistence on `TripPlace.polyline`, and fail-soft GeoJSON LineStrings (change `harden-p6-planner-api-v2` / P6 step 6.0).

## Requirements

### Requirement: RoutingProvider exposes fail-soft route polylines
The system SHALL extend `RoutingProvider` with `route_polyline(waypoints: list[tuple[float, float]]) -> str | None` for an ordered waypoint list of length ≥ 2. The OSRM adapter MUST wrap existing `geo.osrm.get_route` and return `encoded_polyline` when the route is not a haversine fallback; otherwise it MUST return `None`. The method MUST NOT raise solely because geometry is unavailable. `travel_engine` MUST call this only via the injected Protocol (no direct `src.geo` imports).

#### Scenario: Real geometry when OSRM succeeds
- **WHEN** `OsrmRoutingProvider.route_polyline` is called with ≥2 waypoints and `get_route` returns a non-fallback result with geometry
- **THEN** the returned value is the encoded polyline string

#### Scenario: Haversine fallback yields no polyline
- **WHEN** routing falls back to haversine (`fallback_used` true) or geometry is missing
- **THEN** `route_polyline` returns `None` and does not raise

### Requirement: OptimizeResult carries leg and day polylines
After the winning stop order is chosen, `optimize_route` MUST populate `OptimizeResult.leg_polylines` (one entry per ordered stop: geometry into that stop from the previous waypoint or base) and `OptimizeResult.day_polyline` (full base+stops path) by calling `route_polyline`. It MUST NOT request geometry during the travel-matrix permutation search. Total additional `route_polyline` invocations per day MUST be at most `len(ordered) + 1`.

#### Scenario: Polylines align to ordered stops
- **WHEN** optimize completes with three ordered stops and a Fake provider returning non-None polylines
- **THEN** `len(leg_polylines) == 3` and `day_polyline` is non-None

#### Scenario: All-None polylines do not abort optimize
- **WHEN** `route_polyline` returns `None` for every call
- **THEN** optimize still returns ordered stops with all-None polyline fields and does not raise

### Requirement: Schedule state persists polyline fields into TripPlace
Planner tools that materialize day schedules from `OptimizeResult` MUST copy `leg_polyline` onto each stop and `day_polyline` onto the day dict in `TravelState.schedule`. `TripService.save_from_state` MUST map `stop["leg_polyline"]` onto `TripPlace.polyline`. GeoJSON builders MUST emit LineString features from persisted polylines when present, and Point-only features for a day when all polylines are None.

#### Scenario: Saved trip retains stop polyline
- **WHEN** `save_from_state` runs on a schedule whose stops include `leg_polyline`
- **THEN** `get_with_places` returns matching non-null `TripPlace.polyline` values

#### Scenario: GeoJSON degrades without lines
- **WHEN** a saved trip has coordinates but all `TripPlace.polyline` values are null
- **THEN** GeoJSON is still a valid FeatureCollection of Points with no LineString for that day and no 500
