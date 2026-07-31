## 1. Prep

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step5.md` steps 5.12–5.14 (+ Decision Log #10/#15; design: emit, last_known_state, always-eval after generate)
- [x] 1.2 Confirm prerequisites: 5.1–5.11 real; `get_compiled_graph` + evaluation service/repo real; `src/planner/service.py` still stub; `PLANNER_GENERATION_TIMEOUT_SECONDS` in config; no HTTP `/planner/generate` registered

## 2. Step 5.12 — emit wiring + PlannerService

- [x] 2.1 Extend `tool_executor_node` to optionally call `config["configurable"]["emit"](event, data, state_snapshot=working_state)` after applied tool results (no-op if missing); still sole `execute_tool` caller
- [x] 2.2 Implement `PlannerService.generate` — fresh `TravelState` + `ToolContext` per invoke; `get_compiled_graph()`; `_capture_and_emit` updates `last_known_state` outside `wait_for`; timeout merges `generation_timeout` + `abort_triggered`; always `await record_evaluation(final)`; optional `on_event`
- [x] 2.3 Run step 5.12 ✅ snippet (`wait_for` in `generate` source); confirm no FastAPI router registration

## 3. Step 5.13 — tool-loop tests

- [x] 3.1 Create `tests/planner/test_tool_loop.py` with mocked LLM + FakeRoutingProvider; cover happy path, REPLAN bound, max tools + eval, clarification exit, finish_plan gate, wrong-phase, no-tool nudge via executor, concurrent ctx isolation, tool_trace accumulate (≥4), timeout nonempty eval, stuck-detector abort
- [x] 3.2 Ensure `tests/planner/test_phase_transitions.py` + `tests/core/test_llm_chat_with_tools.py` still pass; add import-guard asserts if missing
- [x] 3.3 Run `python -m pytest tests/planner tests/core/test_llm_chat_with_tools.py -v` then `python -m pytest tests/ -v` — failing tests block 5.14

## 4. Step 5.14 — smoke + context

- [x] 4.1 Create `scripts/test_agent.py` — sectioned fail-loud smoke via `PlannerService.generate` (Darjeeling + `raw_input="3 days offbeat photography budget"`); sections 1–8 required, Langfuse optional
- [ ] 4.2 Run `python scripts/test_agent.py` + import-guard Select-String checks from step5; assert `/planner/generate` still unregistered
- [ ] 4.3 Update `docs/context.md` **only after** smoke + full pytest green: Progress 5.1–5.14 ✅; Implemented modules include service bridge; Next → P6.1; stubs keep trips CRUD + planner HTTP; do not claim P6 complete
