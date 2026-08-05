## Purpose

P5 PLAN / VALIDATE / control / REPLAN planner tools (step 5.3): route, schedule, validate, finish, clarify, and recovery actions.

## Requirements

### Requirement: PLAN tools build_route and build_schedule
The project SHALL implement `build_route` and `build_schedule` for PLAN phase.

`build_route` MUST call `allocate_days` then per-day `optimize_route` with `ctx.routing` and base lat/lng, and emit route + `dropped_stops` in `ToolResult.data`, setting `used_osrm_fallback` when any `RouteLeg.used_fallback` is true. Each route day dict MUST also carry `leg_polylines` and `day_polyline` from that day's `OptimizeResult` (may be all-None).

`build_schedule` MUST call `build_day_schedule` per day and emit `TravelState.schedule` as a **list of day dicts** (locked step 6.0 shape): each day has `day`, `stops` (flat stop dicts including `suggested_start_time`, `place_id`, `order`, `travel_time_min`, `leg_polyline`), `total_travel_min`, `total_distance_km` (when available), and `day_polyline`. Stop `leg_polyline` MUST be copied from the corresponding route day's `leg_polylines[i]`; `day_polyline` from the route day. Bare `list[list[stop]]` schedule output is FORBIDDEN after this change.

#### Scenario: Fake routing works in tests
- **WHEN** `build_route` is invoked with a FakeRoutingProvider
- **THEN** it returns `ok=True` (or soft-fail codes) without calling live OSRM and never raises

#### Scenario: Fake provider yields timed schedule
- **WHEN** `build_route` then `build_schedule` are invoked with a FakeRoutingProvider
- **THEN** schedule is a non-empty list of day dicts and every stop has `suggested_start_time`

#### Scenario: Polylines thread into schedule stops
- **WHEN** optimize results include non-None `leg_polylines` / `day_polyline`
- **THEN** `build_schedule` day dicts expose matching `stops[i].leg_polyline` and `day_polyline`

### Requirement: validate_itinerary tool
The project SHALL implement `validate_itinerary` for VALIDATE. It MUST map schedule/route into travel_engine `TripItinerary` / `DayPlan` using the locked field mapping in `docs/steps/step5.md` step 5.3 (updated for P6.0 day-dict schedule), then call `validate_trip`. `ok=True` iff `ValidationResult.passed`; data MUST include errors/warnings. Empty itinerary MUST fail with `empty_itinerary` semantics from P4.

`validate_itinerary` MUST accept `state["schedule"]` as a list of day dicts with a `stops` list (step 6.0 shape). It MUST map each day's stops into travel_engine `ScheduledStop` / `DayPlan` for `validate_trip` without requiring the obsolete bare list-of-lists schedule.

#### Scenario: Empty itinerary fails validation
- **WHEN** validate runs with no days/stops
- **THEN** `ToolResult.ok` is False (or data shows passed=False with `empty_itinerary`) without raising

#### Scenario: Day-dict schedule validates
- **WHEN** `validate_itinerary` receives a schedule of day dicts with nested `stops` compatible with `ScheduledStop` reconstruction
- **THEN** it builds `TripItinerary` and returns `ok` according to `ValidationResult.passed`

#### Scenario: Empty schedule still fails
- **WHEN** schedule and route are both empty
- **THEN** the tool returns `ok=False` with `empty_itinerary` semantics

### Requirement: finish_plan and ask_clarification control tools
`finish_plan` (WRAP_UP) MUST succeed only if a prior validate was ok OR `abort_triggered` is True; otherwise return `precondition_failed`. On success it MAY assemble final itinerary structure and MUST signal `plan_complete` via `ToolResult.data`.

`ask_clarification` (DISCOVER) MUST return `ok=True` with `needs_clarification` and `clarification_question` in data.

#### Scenario: finish_plan blocked without validate or abort
- **WHEN** `finish_plan` runs with no successful validate and `abort_triggered=False`
- **THEN** the result is `ok=False` with `code="precondition_failed"`

### Requirement: REPLAN recovery tools
The project SHALL implement `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, and `accept_partial` for REPLAN.

- `reoptimize_routes`: re-run route+schedule for all days with current ranked set
- `drop_weakest_stop`: remove lowest-scored stop on worst day; re-route that day
- `expand_poi_search`: increase search top_k by `SEARCH_EXPAND_FACTOR` (named constant, 1.5) then re-search → rank → route → schedule via helpers
- `accept_partial`: set `abort_triggered` true in `ToolResult.data` for phase transition by later `maybe_transition_phase`

Multi-step work under one `execute_tool` call is intentional coarse-graining. Tools MUST NOT call an LLM and MUST NOT raise uncaught exceptions.

#### Scenario: accept_partial signals abort
- **WHEN** `accept_partial` succeeds
- **THEN** `ToolResult.ok` is True and data indicates `abort_triggered=True`
