## Purpose

P5.9 bounded agent ↔ tool_executor loop: agent decides `pending_tool_calls` only; executor is the sole `execute_tool` caller; unconditional stuck-detector.

## Requirements

### Requirement: agent_node decides pending tools only
The project SHALL implement `async def agent_node(state, config) -> dict` in `src/planner/graph/nodes/agent.py` such that:

- If `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` (from `get_settings()`), it MUST set `abort_triggered=True`, `agent_phase` to WRAP_UP, `pending_tool_calls=[]`, and return without calling the LLM.
- Otherwise it MUST bind tools via `get_tools_for_phase(state.agent_phase)` and call `chat_with_tools(build_agent_messages(state), tools, tool_choice="auto")` only through `src/core/llm/client.py`.
- On tool_calls → return `{"pending_tool_calls": ...}` (PendingToolCall-compatible dicts).
- On no tool_calls → nudge once with `tool_choice="required"`; if still none → synthesize phase-default `PendingToolCall` from `DEFAULT_TOOL_BY_PHASE` with `arguments_json="{}"` and append warning `agent_no_tool_call_default_used` (and nudge warning when nudge path used).
- On `WandrLLMError` → synthesize the same phase-default pending call and increment `llm_retry_count`.
- MUST NEVER call `execute_tool` or import tool implementation modules.

#### Scenario: Max tool calls aborts without LLM
- **WHEN** `agent_node` runs with `tool_loop_count >= PLANNER_MAX_TOOL_CALLS`
- **THEN** returned state has `abort_triggered=True`, WRAP_UP phase, empty `pending_tool_calls`, and no LLM call is required

#### Scenario: No-tool path synthesizes phase default
- **WHEN** `chat_with_tools` returns content-only for auto and required
- **THEN** `pending_tool_calls` contains the phase default tool name and warning `agent_no_tool_call_default_used` is present

#### Scenario: Agent source has no execute_tool call
- **WHEN** `agent.py` is scanned for `execute_tool(`
- **THEN** there are zero matches

### Requirement: tool_executor_node is sole execute_tool caller
The project SHALL implement `async def tool_executor_node(state, config) -> dict` in `src/planner/graph/nodes/tool_executor.py` such that:

- `ToolContext` MUST come only from `config["configurable"]["tool_context"]`.
- For each pending call: parse input → `await execute_tool(...)` → `apply_tool_result` → `maybe_transition_phase` on a working copy of state.
- Clear `pending_tool_calls` after the batch; return full extended `tool_trace` / `warnings` / `errors` lists (last-write-wins).
- MUST run `run_stuck_detector` unconditionally at end of every cycle (including unknown_tool / precondition failures).
- Tool soft-failures MUST NOT raise out of the node.

#### Scenario: Executor applies results via sole writer
- **WHEN** one pending call succeeds through `execute_tool`
- **THEN** planning fields are updated only via `apply_tool_result` and a `tool_trace` entry is present

#### Scenario: Nodes do not import tool impl modules
- **WHEN** `src/planner/graph/nodes` is scanned for imports of tool body modules (`check_readiness`, `search_places`, `rank_places`, `build_route`, etc.)
- **THEN** there are zero matches (registry / schemas / orchestration only)

### Requirement: Unconditional stuck-detector advances or aborts
`run_stuck_detector(state)` MUST run at the end of every `tool_executor_node` cycle. It MUST track a compact progress fingerprint (phase + lengths of candidate/ranked/route/schedule working lists, plus available validation error codes). If the fingerprint is unchanged for `PLANNER_AGENT_PHASE_STUCK_LIMIT` consecutive cycles:

- Phase in {DISCOVER, PLAN, VALIDATE}: auto-advance to next happy-path phase and append warning `phase_stuck_auto_advance`.
- Phase REPLAN: set `abort_triggered=True`, phase WRAP_UP, warning `phase_stuck_replan_abort`.
- Phase WRAP_UP: force a finish / `plan_complete` attempt path consistent with step5 locks.

The detector MUST NOT be skipped when the only outcome was `unknown_tool`.

#### Scenario: Persistent unknown tools hit stuck limit
- **WHEN** consecutive executor cycles produce no fingerprint progress for `PLANNER_AGENT_PHASE_STUCK_LIMIT` cycles
- **THEN** the stuck path mutates phase / abort flags as specified above without waiting for wall-clock generation timeout alone

### Requirement: tool_executor emits optional state snapshots
The project SHALL extend `tool_executor_node` in `src/planner/graph/nodes/tool_executor.py` so that after applying tool results (at minimum once per pending batch, preferably after each `apply_tool_result`), it invokes an optional emit callable from `config["configurable"].get("emit")` as `emit(event, data, state_snapshot=working_state)` when present. If `emit` is missing, the node MUST behave as today (no-op). Emit MUST NOT become a second pathway for `execute_tool` or state mutation beyond the snapshot argument for service-level `last_known_state`.

#### Scenario: Emit updates service checkpoint without requiring HTTP
- **WHEN** `generate` supplies `emit` via configurable and a tool cycle completes
- **THEN** `emit` is called with a state snapshot reflecting applied tool results so timeout recovery can retain non-empty `tool_trace`

#### Scenario: Missing emit does not break direct graph invoke
- **WHEN** `tool_executor_node` runs without `configurable["emit"]`
- **THEN** tools still execute and state is returned normally
