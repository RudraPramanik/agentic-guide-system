## ADDED Requirements

### Requirement: tool_executor emits optional state snapshots
The project SHALL extend `tool_executor_node` in `src/planner/graph/nodes/tool_executor.py` so that after applying tool results (at minimum once per pending batch, preferably after each `apply_tool_result`), it invokes an optional emit callable from `config["configurable"].get("emit")` as `emit(event, data, state_snapshot=working_state)` when present. If `emit` is missing, the node MUST behave as today (no-op). Emit MUST NOT become a second pathway for `execute_tool` or state mutation beyond the snapshot argument for service-level `last_known_state`.

#### Scenario: Emit updates service checkpoint without requiring HTTP
- **WHEN** `generate` supplies `emit` via configurable and a tool cycle completes
- **THEN** `emit` is called with a state snapshot reflecting applied tool results so timeout recovery can retain non-empty `tool_trace`

#### Scenario: Missing emit does not break direct graph invoke
- **WHEN** `tool_executor_node` runs without `configurable["emit"]`
- **THEN** tools still execute and state is returned normally
