## ADDED Requirements

### Requirement: Typed tool registry

The system SHALL register 12 planner tools in `TOOL_REGISTRY` with Pydantic input/output models, phase tags, and preconditions. Execution MUST go through `execute_tool()` only.

#### Scenario: Wrong-phase tool rejected

- **WHEN** agent attempts a PLAN-phase tool during DISCOVER phase
- **THEN** `ToolResult(ok=False, code="precondition_failed")` is returned without running the tool

### Requirement: Phase-gated tool exposure

The system SHALL expose only tools listed in `PHASE_TOOLS[state.agent_phase]` to the LLM via `get_tools_for_phase()`.

#### Scenario: DISCOVER phase tools

- **WHEN** agent phase is DISCOVER
- **THEN** allowed tools are check_readiness, search_places, rank_places, ask_clarification only

### Requirement: Bounded tool loop

The system SHALL increment `tool_loop_count` on every tool execution and force WRAP_UP when count ≥ `PLANNER_MAX_TOOL_CALLS`.

#### Scenario: Ceiling triggers abort

- **WHEN** tool_loop_count reaches max before validation passes
- **THEN** `abort_triggered=True` and partial itinerary proceeds to wrap-up

### Requirement: LangGraph agent graph

The system SHALL compile a graph: parse_preferences → agent ↔ tool_executor loop → write_narrative → record_evaluation, with clarification early exit.

#### Scenario: Happy path phase transitions

- **WHEN** rank_places succeeds then build_route and build_schedule succeed and validation passes
- **THEN** phases progress DISCOVER → PLAN → VALIDATE → WRAP_UP

### Requirement: Evaluation always recorded

The system SHALL persist `TripEvaluation` including `tool_trace`, `tool_loop_count`, and resilience signals even on abort.

#### Scenario: Abort still writes evaluation

- **WHEN** generation aborts due to tool ceiling
- **THEN** an evaluation row exists with `abort_triggered=True`
