## MODIFIED Requirements

### Requirement: PLAN tools build_route and build_schedule
The project SHALL implement `build_route` and `build_schedule` for PLAN phase.

`build_route` MUST call `allocate_days` then per-day `optimize_route` with `ctx.routing` and base lat/lng, and emit route + `dropped_stops` in `ToolResult.data`, setting `used_osrm_fallback` when any `RouteLeg.used_fallback` is true. Each route day dict MUST also carry `leg_polylines` and `day_polyline` from that day's `OptimizeResult` (may be all-None).

`build_schedule` MUST call `build_day_schedule` per day and emit `TravelState.schedule` as a **list of day dicts** (locked step 6.0 shape): each day has `day`, `stops` (flat stop dicts including `suggested_start_time`, `place_id`, `order`, `travel_time_min`, `leg_polyline`), `total_travel_min`, `total_distance_km` (when available), and `day_polyline`. Stop `leg_polyline` MUST be copied from the corresponding route day's `leg_polylines[i]`; `day_polyline` from the route day. Bare `list[list[stop]]` schedule output is FORBIDDEN after this change.

#### Scenario: Fake provider yields timed schedule
- **WHEN** `build_route` then `build_schedule` are invoked with a FakeRoutingProvider
- **THEN** schedule is a non-empty list of day dicts and every stop has `suggested_start_time`

#### Scenario: Polylines thread into schedule stops
- **WHEN** optimize results include non-None `leg_polylines` / `day_polyline`
- **THEN** `build_schedule` day dicts expose matching `stops[i].leg_polyline` and `day_polyline`

## ADDED Requirements

### Requirement: validate_itinerary accepts day-dict schedule
`validate_itinerary` MUST accept `state["schedule"]` as a list of day dicts with a `stops` list (step 6.0 shape). It MUST map each day's stops into travel_engine `ScheduledStop` / `DayPlan` for `validate_trip` without requiring the obsolete bare list-of-lists schedule. Empty itinerary MUST still fail with `empty_itinerary` semantics.

#### Scenario: Day-dict schedule validates
- **WHEN** `validate_itinerary` receives a schedule of day dicts with nested `stops` compatible with `ScheduledStop` reconstruction
- **THEN** it builds `TripItinerary` and returns `ok` according to `ValidationResult.passed`

#### Scenario: Empty schedule still fails
- **WHEN** schedule and route are both empty
- **THEN** the tool returns `ok=False` with `empty_itinerary` semantics
