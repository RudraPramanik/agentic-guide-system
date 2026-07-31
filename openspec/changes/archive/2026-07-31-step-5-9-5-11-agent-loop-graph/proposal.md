## Why

P5.1–5.8 delivered tools, orchestration, `TravelState`, agent messages, and `parse_preferences`, but the LangGraph loop and bookend nodes are still step-0.1 stubs. Steps **5.9–5.11** (`docs/steps/step5.md` recommended OpenSpec batch) wire the bounded agent ↔ tool_executor cycle, fixed narrative/evaluation bookends, and a compiled graph — the runtime heart of the planner before the SSE service bridge (5.12).

## What Changes

- Implement `src/planner/graph/nodes/agent.py` — decides `pending_tool_calls` only (LLM / nudge / phase-default synthesize); **never** calls `execute_tool`; max-tool-calls → `abort_triggered` + WRAP_UP
- Implement `src/planner/graph/nodes/tool_executor.py` — sole `execute_tool` caller; `apply_tool_result` + `maybe_transition_phase`; unconditional stuck-detector; full-list returns for list fields
- Add supporting helpers as needed (`DEFAULT_TOOL_BY_PHASE`, `parse_tool_input`, `run_stuck_detector`) colocated with registry/orchestration — not new tool impl modules
- Implement `src/planner/graph/nodes/write_narrative.py` — titles/paragraphs only via `chat_completion`; template fallback on LLM fail; never mutate stop order/times/coords
- Implement `src/evaluation/repository.py` + `service.record_generation(...)` and `src/planner/graph/nodes/record_evaluation.py` — always persist (abort/clarification/success); no new TripEvaluation columns/migrations
- Implement `src/planner/graph/builder.py` — compile once (`parse_preferences` → agent → tool_executor unconditional; conditionals for clarification / plan_complete → narrative → evaluation → END)
- Step ✅ validation snippets from `step5.md` 5.9–5.11 (import + compile proofs; no tool-impl imports in nodes; agent has zero `execute_tool(` calls)

## Capabilities

### New Capabilities
- `planner-agent-tool-executor`: Bounded `agent_node` + `tool_executor_node` with phase defaults, ceiling abort, and unconditional stuck-detector (5.9)
- `planner-narrative-evaluation`: Fixed `write_narrative` + `record_evaluation` bookends and evaluation service/repo persistence (5.10)
- `planner-graph-compile`: Cached compiled LangGraph wiring agent loop + bookends (5.11)

### Modified Capabilities
- (none — `p5-langgraph-runtime-hardening` / `p5-phase-gated-tool-loop` already lock single-executor pathway, stuck-detector, narrative/eval, and graph shape; this change implements those locks)

## Impact

- **Code:** Replace stubs in `nodes/agent.py`, `tool_executor.py`, `write_narrative.py`, `record_evaluation.py`, `builder.py`; flesh out stub `evaluation/repository.py` + `evaluation/service.py`; possibly small helpers on `registry` / `orchestration` / `schemas` (`parse_tool_input`, `DEFAULT_TOOL_BY_PHASE`, stuck fingerprint)
- **Non-goals:** `PlannerService` SSE / `wait_for` (5.12); full `tests/planner/test_tool_loop.py` (5.13); live smoke `scripts/test_agent.py` (5.14); HTTP `POST /planner/generate` (P6); new packages; TripEvaluation schema migration
- **LLM:** Only via `src/core/llm/client.py` (`chat_with_tools` in agent; `chat_completion` in narrative). Batch ✅ proofs use imports/compile (+ mocks if any unit smoke); live key not required for 5.9–5.11 merge gates
- **AGENT.md:** Agent never calls `execute_tool`; ToolContext only from `config["configurable"]["tool_context"]`; tools read-only w.r.t. state; evaluation never skipped; narrative outside tool loop; list fields full-list return
- **Prerequisites:** Met — context Next = P5.9; 5.1–5.8 ✅; target files are ~1-line stubs; `TripEvaluation` columns already exist; `PLANNER_MAX_TOOL_CALLS` / `PLANNER_AGENT_PHASE_STUCK_LIMIT` in config
- **context.md:** After validations pass, mark 5.9–5.11 ✅ and set Next step to 5.12
