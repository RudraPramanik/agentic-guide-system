## Purpose

Route geometry for planner itineraries — `RoutingProvider.route_polyline`, optimizer threading into schedule stops, persistence on `TripPlace.polyline`, and fail-soft GeoJSON LineStrings (change `harden-p6-planner-api-v2` / P6 step 6.0; implemented change `p6-0-route-geometry-polyline`).

## Requirements

### Requirement: RoutingProvider exposes fail-soft route polylines
The system SHALL extend `RoutingProvider` with `route_polyline(waypoints: list[tuple[float, float]]) -> str | None` for an ordered waypoint list of length ≥ 2. The OSRM adapter MUST wrap existing `geo.osrm.get_route` and return `encoded_polyline` when the route is not a haversine fallback and geometry is present; otherwise it MUST return `None`. The method MUST NOT raise solely because geometry is unavailable (including catching unexpected errors from `get_route` and mapping them to `None`). `travel_engine` MUST call this only via the injected Protocol (no direct `src.geo` imports).

#### Scenario: Real geometry when OSRM succeeds
- **WHEN** `OsrmRoutingProvider.route_polyline` is called with ≥2 waypoints and `get_route` returns a non-fallback result with geometry
- **THEN** the returned value is the encoded polyline string

#### Scenario: Haversine fallback yields no polyline
- **WHEN** routing falls back to haversine (`fallback_used` true) or geometry is missing
- **THEN** `route_polyline` returns `None` and does not raise

#### Scenario: Soft-fail on get_route errors
- **WHEN** `get_route` raises (e.g. fewer than 2 waypoints) or returns unexpectedly
- **THEN** `OsrmRoutingProvider.route_polyline` returns `None` and does not propagate the exception

### Requirement: OptimizeResult carries leg and day polylines
After the winning stop order is chosen (including after any drop-retry), `optimize_route` MUST populate `OptimizeResult.leg_polylines` (one entry per ordered stop: geometry into that stop from the previous waypoint or base) and `OptimizeResult.day_polyline` (full base+stops path) by calling `route_polyline`. It MUST NOT request geometry during the travel-matrix permutation search or on intermediate drop-retry attempts that are discarded. Total additional `route_polyline` invocations for the returned day MUST be at most `len(ordered) + 1`. Empty `ordered` MUST yield empty `leg_polylines` and `day_polyline=None` with zero `route_polyline` calls.

#### Scenario: Polylines align to ordered stops
- **WHEN** optimize completes with three ordered stops and a Fake provider returning non-None polylines
- **THEN** `len(leg_polylines) == 3` and `day_polyline` is non-None

#### Scenario: All-None polylines do not abort optimize
- **WHEN** `route_polyline` returns `None` for every call
- **THEN** optimize still returns ordered stops with all-None polyline fields and does not raise

#### Scenario: Empty day skips geometry calls
- **WHEN** `day_places` is empty
- **THEN** `leg_polylines` is empty, `day_polyline` is None, and `route_polyline` is not called

### Requirement: Schedule state persists polyline fields into TripPlace
Planner tools that materialize day schedules from `OptimizeResult` MUST emit `TravelState.schedule` as a list of **day dicts** (not bare stop lists). Each day dict MUST include `day`, `stops` (flat stop dicts with at least `place_id`, timing fields, and `leg_polyline`), `total_travel_min`, and `day_polyline`. `leg_polyline` on stop `i` MUST come from `OptimizeResult.leg_polylines[i]`; `day_polyline` MUST come from `OptimizeResult.day_polyline`.

`TripService.save_from_state` (step **6.1**) MUST map `stop["leg_polyline"]` onto `TripPlace.polyline`. Aggregate `day_polyline` is NOT persisted as its own DB column in 6.1 (no invented column). GeoJSON builders MUST emit LineString features from persisted per-stop polylines when present, and Point-only features for a day when all polylines are None (implemented in step 6.3). Step 6.0 MUST leave schedule carrying these fields so 6.1/6.3 do not re-call OSRM.

#### Scenario: build_schedule day dict includes polylines
- **WHEN** `build_schedule` runs after a successful `build_route` whose optimize results include polylines
- **THEN** each schedule day is a dict with `stops[i].leg_polyline` aligned to that day's `leg_polylines[i]` and `day_polyline` set from the optimize result

#### Scenario: Schedule shape is day dicts
- **WHEN** `build_schedule` succeeds with at least one day
- **THEN** `ToolResult.data["schedule"]` is a list of dicts each containing keys `day` and `stops` (list)

#### Scenario: Saved trip retains stop polyline
- **WHEN** `save_from_state` (6.1) runs on a schedule whose stops include `leg_polyline`
- **THEN** `get_with_places` returns matching non-null `TripPlace.polyline` values

#### Scenario: GeoJSON degrades without lines
- **WHEN** a saved trip has coordinates but all `TripPlace.polyline` values are null
- **THEN** GeoJSON is still a valid FeatureCollection of Points with no LineString for that day and no 500

### Requirement: Hybrid generate path can persist road polylines
When the injected `RoutingProvider` returns non-`None` values from `route_polyline` (e.g. hybrid or full OSRM backend), `optimize_route` / `populate_leg_polylines` and downstream schedule persistence MUST continue to map those strings onto stop `leg_polyline` / `TripPlace.polyline` without requiring a second OSRM pass in `build_geojson`. GeoJSON MUST emit LineString features when persisted polylines decode, and MUST remain Point-only when all polylines are null — no invented coordinates.

#### Scenario: Hybrid geometry reaches GeoJSON LineStrings
- **WHEN** a trip is saved from a schedule whose stops include non-null `leg_polyline` values produced under a hybrid routing backend
- **THEN** `GET` trip GeoJSON includes at least one LineString feature for that day (when decode succeeds) in addition to Point features

#### Scenario: Soft-fail geometry still Point-only
- **WHEN** every `route_polyline` call returns `None` under hybrid or haversine
- **THEN** saved trip GeoJSON remains a valid FeatureCollection of Points with no LineString for that day and no 500
