## ADDED Requirements

### Requirement: P5 execute_tool is a pure reader of planning state
When the P4 `execute_tool` stub is expanded in P5, tool implementations MUST treat planning state as read-only input (explicit state snapshot / read view). They MUST NOT mutate `TravelState` via `ToolContext`. Unknown-tool soft-fail (`ok=False`, `code="unknown_tool"`, never raise) remains mandatory.

#### Scenario: Unknown tool still soft-fails under P5 registry
- **WHEN** `execute_tool` is called with an unregistered name after the full P5 registry exists
- **THEN** it returns `ToolResult(ok=False, code="unknown_tool")` and does not raise

#### Scenario: Tool cannot mutate via context
- **WHEN** a registered tool body runs under P5
- **THEN** state updates are applied only by the graph’s `apply_tool_result` path after the tool returns `ToolResult`
