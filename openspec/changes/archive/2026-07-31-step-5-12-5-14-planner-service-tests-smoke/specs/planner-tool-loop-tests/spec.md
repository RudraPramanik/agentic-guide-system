## ADDED Requirements

### Requirement: tool_loop integration tests cover locked star cases
The project SHALL add `tests/planner/test_tool_loop.py` that exercises the compiled planner graph / `PlannerService.generate` with mocked `chat_with_tools` / `chat_completion` and `FakeRoutingProvider` (and DB seed or mocked tools as needed). The suite MUST include cases for:

- Happy path: phases DISCOVER→…→WRAP_UP; `plan_complete=True`; `tool_loop_count ≤ 8`; every scheduled stop has `suggested_start_time`
- Validation fail → REPLAN tools invoked; `replan_loop_count ≤ PLANNER_MAX_REPLAN_ATTEMPTS`
- Max tool calls → `abort_triggered=True`; evaluation recorded
- `ask_clarification` → `needs_clarification=True`; loop exits without `plan_complete`
- `finish_plan` blocked without validate
- Wrong-phase tool → `precondition_failed`; tool fn not called
- Agent no-tool → nudge → synthesize default pending → executor calls `execute_tool` once; `tool_trace` records default with warning `agent_no_tool_call_default_used`; agent never calls `execute_tool`
- Concurrent `generate()` calls with different `destination_id` against the same cached compiled graph do not leak `ToolContext`
- `tool_trace` accumulates across ≥4 tool_executor cycles (`len == 4`, not 1)
- Timeout after ≥1 tool cycle → evaluation has non-empty `tool_trace` and `generation_timeout`
- Persistent `unknown_tool` → abort via stuck-detector within `PLANNER_AGENT_PHASE_STUCK_LIMIT` cycles — not solely via `tool_loop_count` exhaustion or wall-clock timeout

#### Scenario: Planner tool-loop pytest module exists
- **WHEN** `python -m pytest tests/planner/test_tool_loop.py -v` is run after implementation
- **THEN** the locked star cases above are covered and pass

### Requirement: Existing planner/LLM tests remain green
`tests/planner/test_phase_transitions.py` (if present) and `tests/core/test_llm_chat_with_tools.py` MUST remain part of the verification gate. Import guards (no litellm outside `core/llm/client.py`; no tool-impl imports under `graph/nodes`) MAY live in this module or adjacent tests.

#### Scenario: Planner and chat_with_tools suites pass
- **WHEN** `python -m pytest tests/planner tests/core/test_llm_chat_with_tools.py -v` runs
- **THEN** all tests pass before claiming 5.13 complete
