## MODIFIED Requirements

### Requirement: build_route auto-rank uses the same travel-engine V2 gate
When `build_route` auto-ranks from `candidate_pois` because `ranked_pois` is empty, it MUST honor `TRAVEL_ENGINE_V2_ENABLED` the same way `rank_places` does: flag off ⇒ no normalizer and V2 mode off; flag on ⇒ normalize then `select_places` with V2 mode on. It MUST read the flag only through `get_settings()`. Auto-rank MUST remain a planner-tool concern. `allocate_days` MUST receive that flag as an injected mode. `optimize_route` MUST receive return-to-base mode from the same flag, per the return-to-base requirement in this delta. The travel engine MUST NOT read the setting itself.

#### Scenario: Flag-off auto-rank matches legacy select
- **WHEN** `ranked_pois` is empty, candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is false
- **THEN** auto-rank calls selection with V2 mode off and does not normalize

#### Scenario: Flag-on auto-rank normalizes first
- **WHEN** `ranked_pois` is empty, near-duplicate candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is true
- **THEN** auto-rank normalizes before selection with V2 mode on

## ADDED Requirements

### Requirement: Route and replan tools pass return-to-base from the engine flag
`build_route`, `reoptimize_routes`, `drop_weakest_stop`, and `expand_poi_search` MUST call `optimize_route` with `return_to_base` true only when `TRAVEL_ENGINE_V2_ENABLED` is true, and false when it is false. Each tool MUST read that flag only through `get_settings()`. `allocate_days` and `build_day_schedule` MUST keep receiving the same flag as their existing injected mode. With the flag false, each route day dict MUST keep today's open-jaw `total_travel_min` and MUST NOT set a non-null `return_polyline`. With the flag true, each route day dict MUST carry `total_travel_min` from the return-mode result and MUST carry `return_polyline` (a string, or null when geometry failed). `used_osrm_fallback` MUST be true when any matrix leg, including the return leg, has `used_fallback` true. `len(leg_polylines)` MUST stay equal to the number of ordered stops. These tools MUST NOT add a base sentinel to `ordered`.

#### Scenario: Flag-off route stays open-jaw
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and `build_route` runs with a fake routing provider
- **THEN** `optimize_route` is called with return mode off and the route day has a null `return_polyline`

#### Scenario: Flag-on route includes the return
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and `build_route` runs with a fake routing provider whose matrix includes last-stop→base
- **THEN** `optimize_route` is called with return mode on and the route day's `total_travel_min` includes that return duration

#### Scenario: Replan tools use the same return mode
- **WHEN** `reoptimize_routes` runs with `TRAVEL_ENGINE_V2_ENABLED` true and a fake routing provider
- **THEN** it calls `optimize_route` with return mode on

### Requirement: Engine flag controls whether findings land on planner state
`validate_itinerary` MUST keep collecting V2 findings and MUST keep `VALIDATOR_V2_ENFORCE` default false, so a false enforce flag does not change `ToolResult.ok` relative to `validate_trip`. The tool MUST NOT call a REPLAN tool. `v2_findings` MAY remain on the tool result in both flag states. Orchestration MUST write `v2_findings` onto planner state only when `TRAVEL_ENGINE_V2_ENABLED` is true. When that flag is false, orchestration MUST NOT add `v2_findings` to planner state.

#### Scenario: Flag-off validate does not publish findings onto state
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and `validate_itinerary` returns findings on the tool result
- **THEN** planner state has no `v2_findings` key after the result is applied

#### Scenario: Flag-on validate publishes findings onto state
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and `validate_itinerary` returns a non-empty `v2_findings` list
- **THEN** planner state `v2_findings` equals that list after the result is applied

#### Scenario: Enforce default still does not change the publish bit
- **WHEN** `VALIDATOR_V2_ENFORCE` is false, the engine flag is true, and findings include a blocking code but `validate_trip` passes
- **THEN** `ToolResult.ok` is true
