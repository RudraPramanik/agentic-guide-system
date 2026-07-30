## ADDED Requirements

### Requirement: AgentPhase and PHASE_TOOLS mapping
The planner tools layer SHALL define `AgentPhase` with values `discover`, `plan`, `validate`, `replan`, `wrap_up` and a `PHASE_TOOLS` mapping exactly:

- DISCOVER: `check_readiness`, `search_places`, `rank_places`, `ask_clarification`
- PLAN: `build_route`, `build_schedule`
- VALIDATE: `validate_itinerary`
- REPLAN: `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial`
- WRAP_UP: `finish_plan`

#### Scenario: PHASE_TOOLS covers twelve unique names
- **WHEN** the union of all `PHASE_TOOLS` lists is computed
- **THEN** it contains exactly the twelve blueprint tool names with no extras

### Requirement: ToolContext and support schemas
The project SHALL provide `ToolContext` with `destination_id`, `base_lat`, `base_lng`, `routing`, and optional `db`. `ToolContext` MUST NOT expose mutation callbacks or a writable TravelState reference.

The project SHALL provide `ToolTraceEntry`, `PendingToolCall`, and per-tool Pydantic input models for all twelve tools (empty models allowed when the tool reads only from state/ctx).

#### Scenario: ToolContext has no state writer
- **WHEN** `ToolContext` is constructed for a tool call
- **THEN** it has no API that mutates planning state; tools return `ToolResult` only

### Requirement: Twelve-tool TOOL_REGISTRY with phase-aware execute_tool
`TOOL_REGISTRY` MUST contain exactly twelve `ToolDefinition` entries (fn, input_model, allowed_phases, optional precondition).

`execute_tool(name, input, ctx, state=None)` MUST:
1. Return `ok=False`, `code="unknown_tool"` for unregistered names (never raise)
2. Return `ok=False`, `code="precondition_failed"` when the tool is not allowed for `state.agent_phase` (no fn call)
3. Return `ok=False`, `code="precondition_failed"` when a registered precondition fails
4. Catch exceptions from fn and return `ok=False`, `code="tool_error"` (never raise)

`get_tools_for_phase(phase)` MUST return OpenAI-style function schemas only for tools in `PHASE_TOOLS[phase]`.

#### Scenario: Registry has twelve tools
- **WHEN** `TOOL_REGISTRY` is inspected after step 5.1
- **THEN** `len(TOOL_REGISTRY) == 12`

#### Scenario: Phase-filtered schemas for DISCOVER
- **WHEN** `get_tools_for_phase(AgentPhase.DISCOVER)` is called
- **THEN** the function names equal `PHASE_TOOLS[AgentPhase.DISCOVER]`

#### Scenario: Wrong-phase tool rejected
- **WHEN** `execute_tool("build_route", ...)` runs while `agent_phase` is DISCOVER
- **THEN** the result has `ok=False` and `code` in (`precondition_failed`, `not_implemented`, `unknown_tool`) and the PLAN body is not executed

#### Scenario: Unknown tool soft-fails
- **WHEN** `execute_tool("nope", ...)` is called
- **THEN** the result has `ok=False` and `code="unknown_tool"` and no exception propagates
