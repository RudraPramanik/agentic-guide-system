## 1. Step 5.4 — Verify chat_with_tools

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step5.md` steps 5.4–5.5 before coding
- [x] 1.2 Verify `src/core/llm/client.py` `chat_with_tools` matches contract (tools + tool_choice, parse tool_calls, content-only, tenacity / WandrLLMError) — harden only if a gap exists; do not add a second gateway
- [x] 1.3 Create `tests/core/test_llm_chat_with_tools.py` with mocked litellm: tool_call parse, content-only, exhausted retries → WandrLLMError
- [x] 1.4 Run `python -m pytest tests/core/test_llm_chat_with_tools.py -v` — all green

## 2. Step 5.5 — Phase orchestration helpers

- [x] 2.1 Add `_make_test_state()` (or equivalent fixture helper) with agent_phase, tool_loop_count, tool_trace, replan counters for transition tests
- [x] 2.2 Implement `check_preconditions(name, state)` using phase membership + registered preconditions (incl. finish_plan)
- [x] 2.3 Implement `apply_tool_result(state, name, result, ...)` as sole writer: merge allowed `data` keys, append full `tool_trace`, increment `tool_loop_count` for resolved registry names only (`unknown_tool` does not increment); never raise
- [x] 2.4 Implement `maybe_transition_phase(state, tool_name, result)` per locked transition table; increment `replan_loop_count` only on REPLAN entry; caps from `get_settings()`
- [x] 2.5 Keep `execute_tool` soft-fail + wrong-phase reject before fn (no route/schedule merge inside execute); document call order execute → apply → maybe_transition for 5.9
- [x] 2.6 Export helpers from registry surface; run step 5.5 ✅ import validation for `maybe_transition_phase` and `get_tools_for_phase`

## 3. Tests + context

- [x] 3.1 Add `tests/planner/test_phase_transitions.py` covering: rank_places → PLAN; validate fail + budget → REPLAN; max replan → WRAP_UP abort; wrong-phase fn call count == 0
- [x] 3.2 Run `python -m pytest tests/core/test_llm_chat_with_tools.py tests/planner/ -v` (and full suite if practical) — keep prior planner/tool tests green
- [x] 3.3 Update `docs/context.md`: Progress 5.4–5.5 ✅; Implemented modules for orchestration helpers; Next step → 5.6; remove apply_tool_result / phase transitions from stubs-only
