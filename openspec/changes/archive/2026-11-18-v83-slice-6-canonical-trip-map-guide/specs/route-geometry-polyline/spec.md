## MODIFIED Requirements

### Requirement: Schedule state persists polyline fields into TripPlace
Planner tools that materialize day schedules from `OptimizeResult` MUST emit `TravelState.schedule` as a list of **day dicts** (not bare stop lists). Each day dict MUST include `day`, `stops` (flat stop dicts with at least `place_id`, timing fields, and `leg_polyline`), `total_travel_min`, and `day_polyline`. `leg_polyline` on stop `i` MUST come from `OptimizeResult.leg_polylines[i]`; `day_polyline` MUST come from `OptimizeResult.day_polyline`.

`TripService.save_from_state` (step **6.1**) MUST map `stop["leg_polyline"]` onto `TripPlace.polyline`. Aggregate `day_polyline` is NOT persisted as its own DB column (no invented column). While `CANONICAL_TRIP_V2_ENABLED` is false, GeoJSON builders MUST emit LineString features from persisted per-stop polylines when present, and Point-only features for a day when all polylines are None. While the flag is true, GeoJSON builders MUST emit a LineString only when every routed leg on that day has `geometry_provenance=osrm` and the polyline decodes, and MUST stay Point-only for `haversine_estimate` and `none`. Step 6.0 MUST leave schedule carrying these fields so save and GeoJSON do not re-call OSRM. `build_geojson` MUST remain decode-only.

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

#### Scenario: Flag on mixed provenance does not draw a partial road
- **WHEN** the flag is true and a day has one routed leg labeled `osrm` and another labeled `none`
- **THEN** GeoJSON for that day has points and no LineString

### Requirement: Hybrid generate path can persist road polylines
When the injected `RoutingProvider` returns non-`None` values from `route_polyline` (e.g. hybrid or full OSRM backend), `optimize_route` / `populate_leg_polylines` and downstream schedule persistence MUST continue to map those strings onto stop `leg_polyline` / `TripPlace.polyline` without requiring a second OSRM pass in `build_geojson`. While `CANONICAL_TRIP_V2_ENABLED` is false, GeoJSON MUST emit LineString features when persisted polylines decode, and MUST remain Point-only when all polylines are null — no invented coordinates. While the flag is true, a decoded polyline MUST be emitted as a LineString only under the `osrm` rule in the schedule-persistence requirement, and a null polyline MUST be labeled `haversine_estimate` or `none` rather than drawn as a straight line.

#### Scenario: Hybrid geometry reaches GeoJSON LineStrings
- **WHEN** a trip is saved from a schedule whose stops include non-null `leg_polyline` values produced under a hybrid routing backend and the flag is false
- **THEN** `GET` trip GeoJSON includes at least one LineString feature for that day (when decode succeeds) in addition to Point features

#### Scenario: Soft-fail geometry still Point-only
- **WHEN** every `route_polyline` call returns `None` under hybrid or haversine
- **THEN** saved trip GeoJSON remains a valid FeatureCollection of Points with no LineString for that day and no 500

#### Scenario: Flag on hybrid success is labeled osrm
- **WHEN** the flag is true and every routed leg on a day stored a non-fallback road polyline
- **THEN** the GeoJSON LineString for that day has `geometry_provenance` equal to `osrm`
