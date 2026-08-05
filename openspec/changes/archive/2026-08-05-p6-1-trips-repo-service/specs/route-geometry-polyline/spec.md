## MODIFIED Requirements

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
