## Purpose

P5.5 registry orchestration: preconditions, deterministic phase transitions, and `apply_tool_result` as the sole TravelState writer from tool outcomes (tool_trace / tool_loop_count bookkeeping).

## Requirements

### Requirement: check_preconditions helper
The planner tools layer SHALL expose `check_preconditions(name, state) -> tuple[bool, str | None]` that evaluates registry-level and tool-specific preconditions for a named tool against a read-only state view (including phase membership and `finish_plan` validate-or-abort rules already registered).

#### Scenario: Wrong phase fails precondition
- **WHEN** `check_preconditions("build_route", state)` runs with `agent_phase=DISCOVER`
- **THEN** the result is `(False, ...)` and indicates failure without executing the tool body

#### Scenario: finish_plan without validate fails
- **WHEN** `check_preconditions("finish_plan", state)` runs with no successful validate and `abort_triggered=False`
- **THEN** the result is `(False, ...)`

### Requirement: maybe_transition_phase locked table
The planner tools layer SHALL expose `maybe_transition_phase(state, tool_name, result)` as the only phase mutator in this step (aside from later agent ceiling/stuck paths). The LLM MUST NOT set `agent_phase`.

Transitions MUST follow the locked table in `docs/steps/step5.md`:
- DISCOVER + successful `rank_places` → PLAN
- PLAN + successful `build_schedule` → VALIDATE
- VALIDATE + `validate_itinerary` ok → WRAP_UP
- VALIDATE + errors with replan budget → REPLAN and increment `replan_loop_count` only on REPLAN entry
- VALIDATE + errors with replan exhausted → WRAP_UP with `abort_triggered=True`
- REPLAN + successful replan tool other than `accept_partial` → PLAN
- REPLAN + `accept_partial` (or replan max) → WRAP_UP
- Any with `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → WRAP_UP with `abort_triggered=True`
- DISCOVER + successful `ask_clarification` → `needs_clarification=True`

#### Scenario: rank_places success advances to PLAN
- **WHEN** `maybe_transition_phase` runs after a successful `rank_places` in DISCOVER
- **THEN** `state.agent_phase` becomes PLAN

#### Scenario: validate fail with replan budget enters REPLAN
- **WHEN** `validate_itinerary` returns not-ok and `replan_loop_count < max_replan_attempts`
- **THEN** phase becomes REPLAN and `replan_loop_count` increments exactly once for that entry

#### Scenario: replan exhausted aborts to WRAP_UP
- **WHEN** `validate_itinerary` returns not-ok and replan budget is exhausted
- **THEN** phase becomes WRAP_UP and `abort_triggered` is True

### Requirement: apply_tool_result sole TravelState writer
The planner tools layer SHALL expose `apply_tool_result(state, name, result, ...)` as the sole writer of planning state from tool outcomes. It MUST merge allowed keys from `result.data` into state, append a `ToolTraceEntry` by reading the full current `tool_trace` list and returning/storing the extended list, and MUST NEVER raise.

Tool implementation functions MUST remain read-only and MUST NOT mutate TravelState / planning state directly.

`tool_loop_count` MUST increment exactly once per resolved registry tool outcome applied (including `precondition_failed`). `unknown_tool` MUST NOT increment `tool_loop_count`.

#### Scenario: Successful tool merges data and appends trace
- **WHEN** `apply_tool_result` is called with `ok=True` and `data` containing ranked POIs
- **THEN** state receives the merged fields, `tool_trace` length increases by one, and `tool_loop_count` increases by one

#### Scenario: unknown_tool does not increment loop count
- **WHEN** `apply_tool_result` is called for a result with `code="unknown_tool"`
- **THEN** `tool_loop_count` is unchanged (stuck-detector in step 5.9 remains the backstop; not implemented in this step)

#### Scenario: Wrong-phase rejection has no route side effects
- **WHEN** a wrong-phase tool is rejected with `precondition_failed` before fn execution
- **THEN** `route` / `schedule` fields are unchanged by the failed call’s apply path beyond trace/count bookkeeping

### Requirement: Orchestration helpers are importable
`get_tools_for_phase`, `maybe_transition_phase`, and `apply_tool_result` MUST be importable from the planner tools registry module surface for use by later graph nodes.

#### Scenario: Step 5.5 import validation
- **WHEN** an implementer imports `maybe_transition_phase` and `get_tools_for_phase` from the registry module
- **THEN** both callables are present (step 5.5 ✅ validation)

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
