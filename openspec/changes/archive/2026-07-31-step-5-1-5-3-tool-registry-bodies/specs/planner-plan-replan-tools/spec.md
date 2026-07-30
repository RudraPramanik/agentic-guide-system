## ADDED Requirements

### Requirement: PLAN tools build_route and build_schedule
The project SHALL implement `build_route` and `build_schedule` for PLAN phase.

`build_route` MUST call `allocate_days` then per-day `optimize_route` with `ctx.routing` and base lat/lng, and emit route + `dropped_stops` in `ToolResult.data`, setting `used_osrm_fallback` when any `RouteLeg.used_fallback` is true.

`build_schedule` MUST call `build_day_schedule` per day and emit a schedule where every stop has `suggested_start_time`.

#### Scenario: Fake routing works in tests
- **WHEN** `build_route` is invoked with a FakeRoutingProvider
- **THEN** it returns `ok=True` (or soft-fail codes) without calling live OSRM and never raises

### Requirement: validate_itinerary tool
The project SHALL implement `validate_itinerary` for VALIDATE. It MUST map schedule/route into travel_engine `TripItinerary` / `DayPlan` using the locked field mapping in `docs/steps/step5.md` step 5.3, then call `validate_trip`. `ok=True` iff `ValidationResult.passed`; data MUST include errors/warnings. Empty itinerary MUST fail with `empty_itinerary` semantics from P4.

#### Scenario: Empty itinerary fails validation
- **WHEN** validate runs with no days/stops
- **THEN** `ToolResult.ok` is False (or data shows passed=False with `empty_itinerary`) without raising

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
