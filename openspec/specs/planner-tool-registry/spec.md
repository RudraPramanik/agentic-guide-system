## Purpose

Typed P5 planner tool registry: AgentPhase, PHASE_TOOLS, ToolContext, twelve ToolDefinitions, and phase-aware soft-fail `execute_tool` / `get_tools_for_phase` (steps 5.1+).

## Requirements

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

### Requirement: execute_tool bookkeeping via orchestration
After step 5.5, callers that apply tool outcomes MUST use `apply_tool_result` (registry orchestration) so that every `execute_tool` dispatch whose name resolves in `TOOL_REGISTRY` results in exactly one `tool_loop_count` increment and one `tool_trace` entry, including `precondition_failed` outcomes. Unregistered names (`unknown_tool`) MUST NOT increment `tool_loop_count`.

`execute_tool` itself MUST continue to soft-fail (never raise), reject wrong-phase before calling `fn`, and MUST NOT merge `ToolResult.data` into route/schedule — that remains `apply_tool_result`’s job.

#### Scenario: Wrong-phase rejects without calling fn
- **WHEN** `execute_tool("build_route", ...)` runs while `agent_phase` is DISCOVER
- **THEN** the result has `ok=False` and `code="precondition_failed"` and the tool body is not invoked (spy/mock call count == 0)

#### Scenario: Resolved name bookkeeping on apply
- **WHEN** `execute_tool` returns `precondition_failed` for a registered tool and `apply_tool_result` is invoked
- **THEN** `tool_loop_count` increments by one and a `tool_trace` entry is appended

### Requirement: ToolTraceEntry MAY carry optional fusion diagnostics
`ToolTraceEntry` MUST remain backward compatible for existing fields (`name`, `ok`, `ms`, `phase`, `code`, `fallback_used`). It MAY include an optional diagnostics field (dict or structured optional payload). When `apply_tool_result` processes a `ToolResult` whose data contains fusion diagnostics, it MUST copy that payload onto the appended `tool_trace` entry. Fusion diagnostics MUST NOT be added to TravelState merge keys used for planning fields such as `candidate_pois`.

#### Scenario: Diagnostics land on tool_trace entry
- **WHEN** `apply_tool_result` runs for `search_places` with `fusion_diagnostics` in `ToolResult.data`
- **THEN** the new `tool_trace` entry includes that diagnostics payload and `candidate_pois` merge behavior is unchanged

#### Scenario: Missing diagnostics keeps prior trace shape
- **WHEN** `apply_tool_result` runs for a tool without fusion diagnostics in data
- **THEN** a `tool_trace` entry is still appended with existing required fields and without requiring a diagnostics value
