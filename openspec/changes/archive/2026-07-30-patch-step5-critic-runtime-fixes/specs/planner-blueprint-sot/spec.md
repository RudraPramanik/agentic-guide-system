## ADDED Requirements

### Requirement: ToolContext injection is config-only in master blueprint
`docs/blueprint_final.md` MUST state that `ToolContext` is constructed once per graph invocation and threaded **only** via `RunnableConfig.configurable["tool_context"]`. The prior “closure / configurable” wording MUST be replaced so closures are not an allowed alternative when the compiled graph is a cached singleton.

#### Scenario: Blueprint forbids closure ToolContext
- **WHEN** the ToolContext design block in `docs/blueprint_final.md` is read
- **THEN** it MUST require config-based injection and MUST NOT present a compile-time closure as an allowed threading option for the cached graph

### Requirement: Agent no-tool default synthesizes pending calls in master blueprint
The master blueprint agent / fallback design MUST specify that when nudge + `tool_choice="required"` still yields no tool calls, the agent synthesizes the phase-default as `pending_tool_calls` for `tool_executor` — it MUST NOT execute the default tool inside `agent_node`.

#### Scenario: Blueprint agent does not call execute_tool
- **WHEN** the deterministic no-tool fallback table / agent_node design in `docs/blueprint_final.md` is read
- **THEN** the default-tool path is described as pending-call synthesis for the executor, not as agent-side `execute_tool`
