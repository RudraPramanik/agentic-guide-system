## MODIFIED Requirements

### Requirement: ToolResult envelope and execute_tool stub
The project SHALL provide `src/planner/tools/schemas.py` with a Pydantic `ToolResult` model containing at least: `ok: bool`, `code: str | None`, `message: str | None`, `data: dict | None`, `fallback_used: bool = False`.

The project SHALL provide `src/planner/tools/registry.py` with async `execute_tool(name: str, input: BaseModel | dict, ctx: object | None = None, state=None) -> ToolResult`.

After steps 5.1–5.3, `execute_tool` MUST:
- Dispatch via a `TOOL_REGISTRY` of exactly twelve named tools (see `planner-tool-registry`)
- Return `ToolResult(ok=False, code="unknown_tool", ...)` when `name` is not registered
- NEVER raise for unknown tools, wrong-phase, precondition failure, or tool-body exceptions
- NOT implement LangGraph nodes or HTTP planner routes (those remain later P5 / P6)

P4-era empty-registry behavior is superseded once the twelve tools are registered; unknown-tool soft-fail remains mandatory.

#### Scenario: Unknown tool is a soft failure
- **WHEN** `execute_tool` is called with an unregistered name
- **THEN** it returns a `ToolResult` with `ok=False` and `code="unknown_tool"` and does not raise

#### Scenario: Envelope types import cleanly
- **WHEN** `ToolResult` and `execute_tool` are imported from the planner tools modules
- **THEN** the import succeeds without loading LangGraph or requiring live external services

### Requirement: P5 execute_tool is a pure reader of planning state
When the P4 `execute_tool` stub is expanded in P5, tool implementations MUST treat planning state as read-only input (explicit state snapshot / read view). They MUST NOT mutate `TravelState` via `ToolContext`. Unknown-tool soft-fail (`ok=False`, `code="unknown_tool"`, never raise) remains mandatory. State updates are expressed in `ToolResult.data` for later application by the graph’s `apply_tool_result` path (step 5.5+).

#### Scenario: Unknown tool still soft-fails under P5 registry
- **WHEN** `execute_tool` is called with an unregistered name after the full P5 registry exists
- **THEN** it returns `ToolResult(ok=False, code="unknown_tool")` and does not raise

#### Scenario: Tool cannot mutate via context
- **WHEN** a registered tool body runs under P5
- **THEN** state updates are expressed only in `ToolResult.data` for later `apply_tool_result`; `ToolContext` has no writable `TravelState` reference
