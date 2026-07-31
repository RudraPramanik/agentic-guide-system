## ADDED Requirements

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
