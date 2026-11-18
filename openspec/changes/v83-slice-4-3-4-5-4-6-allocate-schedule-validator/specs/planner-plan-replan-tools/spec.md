## MODIFIED Requirements

### Requirement: build_route auto-rank uses the same travel-engine V2 gate
When `build_route` auto-ranks from `candidate_pois` because `ranked_pois` is empty, it MUST honor `TRAVEL_ENGINE_V2_ENABLED` the same way `rank_places` does: flag off ⇒ no normalizer and V2 mode off; flag on ⇒ normalize then `select_places` with V2 mode on. It MUST read the flag only through `get_settings()`. Auto-rank MUST remain a planner-tool concern. `optimize_route` MUST stay on its current signature. `allocate_days` MUST receive the same flag as an injected mode.

#### Scenario: Flag-off auto-rank matches legacy select
- **WHEN** `ranked_pois` is empty, candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is false
- **THEN** auto-rank calls selection with V2 mode off and does not normalize

#### Scenario: Flag-on auto-rank normalizes first
- **WHEN** `ranked_pois` is empty, near-duplicate candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is true
- **THEN** auto-rank normalizes before selection with V2 mode on

### Requirement: validate_itinerary tool
The project SHALL implement `validate_itinerary` for VALIDATE. It MUST map schedule/route into travel_engine `TripItinerary` / `DayPlan` using the locked field mapping in `docs/steps/step5.md` step 5.3 (updated for P6.0 day-dict schedule), then call `validate_trip`. Empty itinerary MUST fail with `empty_itinerary` semantics from P4.

`validate_itinerary` MUST accept `state["schedule"]` as a list of day dicts with a `stops` list (step 6.0 shape). It MUST map each day's stops into travel_engine `ScheduledStop` / `DayPlan` for `validate_trip` without requiring the obsolete bare list-of-lists schedule.

The tool MUST read `VALIDATOR_V2_ENFORCE` only through `get_settings()`. The default MUST be false. It MUST collect V2 findings on every non-empty validation. While the flag is false, `ToolResult.ok`, `errors`, `warnings`, and `validation_result` MUST match `validate_trip` alone. Findings MUST be logged and MAY be returned under a data key that orchestration does not merge into `TravelState`. While the flag is true, `ok` MUST be false when `validate_trip` does not pass or any finding has `blocks_publish` true. The tool MUST NOT call a REPLAN tool.

#### Scenario: Empty itinerary fails validation
- **WHEN** validate runs with no days/stops
- **THEN** `ToolResult.ok` is False (or data shows passed=False with `empty_itinerary`) without raising

#### Scenario: Day-dict schedule validates
- **WHEN** `validate_itinerary` receives a schedule of day dicts with nested `stops` compatible with `ScheduledStop` reconstruction and enforce is false
- **THEN** it builds `TripItinerary` and returns `ok` according to `ValidationResult.passed`

#### Scenario: Empty schedule still fails
- **WHEN** schedule and route are both empty
- **THEN** the tool returns `ok=False` with `empty_itinerary` semantics

#### Scenario: Shadow findings do not change the publish bit
- **WHEN** enforce is false and findings include a blocking code but `validate_trip` passes
- **THEN** `ToolResult.ok` is true and `validation_result` matches the v6.1 result

#### Scenario: Enforce blocks on a critical finding
- **WHEN** enforce is true and findings include a code with `blocks_publish` true
- **THEN** `ToolResult.ok` is false

## ADDED Requirements

### Requirement: Route and schedule tools inject the engine flag
`build_route` MUST pass `TRAVEL_ENGINE_V2_ENABLED` into `allocate_days` as the injected mode on every call, including when `ranked_pois` is already filled. `build_schedule` MUST pass that same flag into `build_day_schedule`. Both tools MUST read the flag only through `get_settings()`. With the flag false, route day membership and schedule times MUST match the current tools. The tools MUST NOT pass the flag into `optimize_route`.

#### Scenario: Flag-off build_route packing is unchanged
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and `build_route` runs with a fake routing provider
- **THEN** `allocate_days` is invoked with V2 mode off

#### Scenario: Flag-on build_schedule uses V2 timing
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and `build_schedule` runs
- **THEN** `build_day_schedule` is invoked with V2 mode on and `preserve_order` stays false
