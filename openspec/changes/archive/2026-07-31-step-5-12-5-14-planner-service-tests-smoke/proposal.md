## Why

P5.1–5.11 delivered the phase-gated tool loop, narrative/eval bookends, and a compiled LangGraph singleton, but there is still no service-level runner with a generation timeout or event bridge — and no integration/smoke proof that the loop works end-to-end. Steps **5.12–5.14** (`docs/steps/step5.md` / `docs/blueprint_final.md` v6.1 recommended OpenSpec batch) close P5: `PlannerService.generate` with `wait_for` + `last_known_state`, tool-loop pytest, and `scripts/test_agent.py` + `context.md` ship gate.

## What Changes

- Implement `src/planner/service.py` — `PlannerService.generate(...)` builds initial `TravelState` + **fresh** `ToolContext` per invoke; invokes `get_compiled_graph()` with `config["configurable"]` (`tool_context`, `emit`); wraps `ainvoke` in `asyncio.wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`; on timeout merges `last_known_state` + `generation_timeout` / `abort_triggered`; **always** persists evaluation for clarification/timeout short-circuits (and any path that skipped the graph `record_evaluation` node)
- Wire emit hooks so nodes (at minimum `tool_executor` after each applied tool result) call `emit(event, data, state_snapshot=...)` from configurable — updates service-level `last_known_state` outside the cancellable task
- Create `tests/planner/test_tool_loop.py` with the locked ★ cases (happy path, REPLAN, max tools, clarification, finish_plan gate, wrong-phase, no-tool nudge via executor, concurrent ctx isolation, tool_trace accumulate, timeout nonempty eval, stuck-detector abort)
- Keep/extend `tests/planner/test_phase_transitions.py` + existing `tests/core/test_llm_chat_with_tools.py`; add import-guard asserts as needed
- Create `scripts/test_agent.py` — sectioned P5 smoke via `PlannerService.generate` (Darjeeling + LLM keys); fail loud by section
- Update `docs/context.md` **only after** smoke + full pytest green: 5.1–5.14 ✅, Next → P6.1; do **not** register HTTP `/planner/generate`

## Capabilities

### New Capabilities
- `planner-service-sse-bridge`: Service-level generation runner with emit callbacks, fresh ToolContext per invoke, `wait_for` ceiling, and evaluation on timeout/clarification short-circuit (5.12)
- `planner-tool-loop-tests`: Integration coverage for the agent↔executor loop, concurrency isolation, timeout eval, and stuck-detector (5.13)
- `planner-agent-smoke`: End-to-end `scripts/test_agent.py` smoke + P5-complete `context.md` update (5.14)

### Modified Capabilities
- `planner-agent-tool-executor` (delta): `tool_executor_node` MUST optionally invoke configurable `emit` with a state snapshot after applying tool results so service-level `last_known_state` tracks real progress (required by 5.12 timeout design)

## Impact

- **Code:** Replace stub `src/planner/service.py`; small emit wiring in `tool_executor` (and any other nodes needed for useful checkpoints); new `tests/planner/test_tool_loop.py`; new `scripts/test_agent.py`; `docs/context.md` at end of batch
- **Non-goals:** FastAPI `POST /planner/generate` StreamingResponse / SSE queue / disconnect cancel (**P6**); trips CRUD / guest persistence (**P6**); new packages; TripEvaluation schema migration; rewiring clarification to go through narrative in-graph (service owns short-circuit eval)
- **Settings:** `PLANNER_GENERATION_TIMEOUT_SECONDS` (and existing planner bounds) via `get_settings()` only
- **AGENT.md:** ToolContext only via configurable; no ToolContext closure at compile time; LLM only via `core/llm/client.py`; evaluation never skipped on abort/timeout/clarification; HTTP generate not claimed live
- **Prerequisites:** Met — context Next = P5.12; 5.1–5.11 ✅; `get_compiled_graph` + evaluation service real; `service.py` still ~1-line stub
- **context.md:** After 5.14 validations pass, mark 5.1–5.14 ✅ and set Next step to P6.1
