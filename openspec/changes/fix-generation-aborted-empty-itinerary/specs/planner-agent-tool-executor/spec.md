## MODIFIED Requirements

### Requirement: agent_node decides pending tools only
The project SHALL implement `async def agent_node(state, config) -> dict` in `src/planner/graph/nodes/agent.py` such that:

- If `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` (from `get_settings()`), it MUST set `abort_triggered=True`, `agent_phase` to WRAP_UP, `pending_tool_calls=[]`, and return without calling the LLM.
- Otherwise it MUST bind tools via `get_tools_for_phase(state.agent_phase)` and call `chat_with_tools(build_agent_messages(state), tools, tool_choice="auto")` only through `src/core/llm/client.py`.
- On tool_calls → return `{"pending_tool_calls": ...}` (PendingToolCall-compatible dicts).
- On no tool_calls → nudge once with `tool_choice="required"`; if still none → synthesize a **state-aware** phase-default `PendingToolCall` (allowed in the current phase) with `arguments_json="{}"` and append warning `agent_no_tool_call_default_used` (and nudge warning when nudge path used).
- On `WandrLLMError` → synthesize the same state-aware default pending call and increment `llm_retry_count`.
- MUST NEVER call `execute_tool` or import tool implementation modules.

State-aware DISCOVER defaults MUST progress: no readiness yet → `check_readiness`; readiness present and no `candidate_pois` → `search_places`; candidates present and no `ranked_pois` → `rank_places`. PLAN defaults MUST use `build_schedule` when a route already exists, otherwise `build_route`. Other phases MAY keep using `DEFAULT_TOOL_BY_PHASE`.

#### Scenario: Max tool calls aborts without LLM
- **WHEN** `agent_node` runs with `tool_loop_count >= PLANNER_MAX_TOOL_CALLS`
- **THEN** returned state has `abort_triggered=True`, WRAP_UP phase, empty `pending_tool_calls`, and no LLM call is required

#### Scenario: No-tool path synthesizes phase default
- **WHEN** `chat_with_tools` returns content-only for auto and required
- **THEN** `pending_tool_calls` contains a current-phase default tool name and warning `agent_no_tool_call_default_used` is present

#### Scenario: LLM failure after readiness synthesizes search_places
- **WHEN** `agent_node` runs in DISCOVER with a readiness score already on state, empty `candidate_pois`, and `chat_with_tools` raises `WandrLLMError`
- **THEN** `pending_tool_calls` contains `search_places` (not another `check_readiness`)

#### Scenario: Agent source has no execute_tool call
- **WHEN** `agent.py` is scanned for `execute_tool(`
- **THEN** there are zero matches

### Requirement: Unconditional stuck-detector advances or aborts
`run_stuck_detector(state)` MUST run at the end of every `tool_executor_node` cycle. It MUST track a compact progress fingerprint (phase + lengths of candidate/ranked/route/schedule working lists, plus available validation error codes). If the fingerprint is unchanged for `PLANNER_AGENT_PHASE_STUCK_LIMIT` consecutive cycles:

- Phase DISCOVER with empty `candidate_pois`: MUST NOT auto-advance to PLAN. MUST set `abort_triggered=True`, phase WRAP_UP, and append a `phase_stuck*` warning.
- Phase DISCOVER with at least one candidate: auto-advance to PLAN and append warning `phase_stuck_auto_advance`.
- Phase PLAN with no usable schedule (no day with stops): MUST NOT auto-advance to VALIDATE. MUST set `abort_triggered=True`, phase WRAP_UP, and append a `phase_stuck*` warning.
- Phase PLAN with a usable schedule: auto-advance to VALIDATE and append warning `phase_stuck_auto_advance`.
- Phase VALIDATE: auto-advance to WRAP_UP and append warning `phase_stuck_auto_advance`.
- Phase REPLAN: set `abort_triggered=True`, phase WRAP_UP, warning `phase_stuck_replan_abort`.
- Phase WRAP_UP: force a finish / `plan_complete` attempt path consistent with step5 locks.

The detector MUST NOT be skipped when the only outcome was `unknown_tool`.

#### Scenario: Persistent unknown tools hit stuck limit
- **WHEN** consecutive executor cycles produce no fingerprint progress for `PLANNER_AGENT_PHASE_STUCK_LIMIT` cycles
- **THEN** the stuck path mutates phase / abort flags as specified above without waiting for wall-clock generation timeout alone

#### Scenario: Stuck DISCOVER without POIs does not enter PLAN
- **WHEN** DISCOVER is stuck for `PLANNER_AGENT_PHASE_STUCK_LIMIT` cycles with empty `candidate_pois`
- **THEN** phase becomes WRAP_UP with `abort_triggered=True` and does not become PLAN
