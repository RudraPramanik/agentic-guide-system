## Purpose

Minimal planner tool envelope for P4 step 4.8 (`ToolResult` + `execute_tool` stub). Full PHASE_TOOLS registry is P5.

## Requirements

### Requirement: ToolResult envelope and execute_tool stub
The project SHALL extend `src/planner/tools/schemas.py` with a Pydantic `ToolResult` model containing at least: `ok: bool`, `code: str | None`, `message: str | None`, `data: dict | None`.

The project SHALL extend `src/planner/tools/registry.py` with async `execute_tool(name: str, input: BaseModel | dict, ctx: object | None = None) -> ToolResult` as locked in `docs/steps/step4.md` step 4.8.

P4 `execute_tool` MUST:
- Return `ToolResult(ok=False, code="unknown_tool", ...)` when `name` is not present in a minimal registry dict (empty or placeholder keys without real tool bodies)
- NEVER raise for unknown tools
- NOT implement full `PHASE_TOOLS`, the 12-tool registry, or tool body modules (those are P5)

#### Scenario: Unknown tool is a soft failure
- **WHEN** `execute_tool` is called with an unregistered name
- **THEN** it returns a `ToolResult` with `ok=False` and `code="unknown_tool"` and does not raise

#### Scenario: Envelope types import cleanly
- **WHEN** `ToolResult` and `execute_tool` are imported from the planner tools modules
- **THEN** the import succeeds without loading LangGraph or real tool implementations

### Requirement: P5 execute_tool is a pure reader of planning state
When the P4 `execute_tool` stub is expanded in P5, tool implementations MUST treat planning state as read-only input (explicit state snapshot / read view). They MUST NOT mutate `TravelState` via `ToolContext`. Unknown-tool soft-fail (`ok=False`, `code="unknown_tool"`, never raise) remains mandatory.

#### Scenario: Unknown tool still soft-fails under P5 registry
- **WHEN** `execute_tool` is called with an unregistered name after the full P5 registry exists
- **THEN** it returns `ToolResult(ok=False, code="unknown_tool")` and does not raise

#### Scenario: Tool cannot mutate via context
- **WHEN** a registered tool body runs under P5
- **THEN** state updates are applied only by the graph’s `apply_tool_result` path after the tool returns `ToolResult`
