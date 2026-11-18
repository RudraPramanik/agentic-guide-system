## ADDED Requirements

### Requirement: Engine flag maps one finding to one existing replan tool
When `TRAVEL_ENGINE_V2_ENABLED` is false, phase transitions MUST stay on the locked table. Findings MUST NOT set `force_next_tool`. The REPLAN stuck path MUST keep its current abort warning and MUST NOT force `accept_partial`.

When `TRAVEL_ENGINE_V2_ENABLED` is true and validation is not ok with replan budget remaining, orchestration MUST choose at most one repair tool and set `force_next_tool` to it before the model picks. The tool MUST be a `suggested_action` that is exactly `reoptimize_routes`, `drop_weakest_stop`, or `expand_poi_search`. Among those findings, one with `blocks_publish` true wins; ties break by the stable finding-code registry order. If none block publish, the same registry order applies. A null or any other action MUST be ignored. If no legal action remains, orchestration MUST NOT force a repair tool and MUST NOT register a new tool. `accept_partial` MUST NOT be chosen as that mapped repair. `PLANNER_MAX_REPLAN_ATTEMPTS` MUST NOT be raised. The model MUST NOT set `agent_phase`.

#### Scenario: Flag off does not force a repair
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and `validate_itinerary` is not ok with replan budget remaining
- **THEN** phase becomes REPLAN and `force_next_tool` is not set from `v2_findings`

#### Scenario: Blocking finding forces its existing tool
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true, replan budget remains, and findings include a blocking `OPENING_HOURS_CONFLICT` whose `suggested_action` is `reoptimize_routes`
- **THEN** `force_next_tool` is `reoptimize_routes`

#### Scenario: Unknown action is ignored
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and the only `suggested_action` values are null or a name that is not one of the three repair tools
- **THEN** `force_next_tool` is not set to that name and no new tool is registered

### Requirement: No progress forces the existing accept_partial tool
When `TRAVEL_ENGINE_V2_ENABLED` is true, a REPLAN repair that leaves the multiset of finding codes and the set of dropped place ids unchanged MUST set `force_next_tool` to `accept_partial` instead of another repair. Applying that existing tool MUST set `abort_triggered` and move the phase to WRAP_UP, using the tool's current behavior. When the replan budget is already exhausted, the locked exhausted path MUST still move to WRAP_UP with `abort_triggered` and MUST NOT start another repair. When the flag is false, this no-progress rule MUST NOT run.

#### Scenario: Unchanged findings accept the partial plan
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and a successful repair tool leaves the same finding codes and the same dropped place ids
- **THEN** the next forced tool is `accept_partial` and a further `drop_weakest_stop` or `reoptimize_routes` is not forced

#### Scenario: Replan budget still ends the loop
- **WHEN** `validate_itinerary` is not ok and `replan_loop_count` is already at `max_replan_attempts`
- **THEN** phase becomes WRAP_UP, `abort_triggered` is true, and no repair tool is forced

#### Scenario: Flag off keeps the current stuck abort
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and the REPLAN stuck detector fires
- **THEN** the phase moves on the current stuck path and `accept_partial` is not forced by this rule
