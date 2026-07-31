## 1. Prep

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step5.md` steps 5.9–5.11 (+ locked decisions: defaults, stuck-detector, list accumulation, ToolContext)
- [x] 1.2 Confirm prerequisites: 5.1–5.8 real; `agent.py` / `tool_executor.py` / `write_narrative.py` / `record_evaluation.py` / `builder.py` / `evaluation/{repository,service}.py` still stubs; `PLANNER_MAX_TOOL_CALLS` + `PLANNER_AGENT_PHASE_STUCK_LIMIT` present in config

## 2. Step 5.9 helpers

- [x] 2.1 Add `DEFAULT_TOOL_BY_PHASE` (locked table) next to phase constants / schemas; export for agent
- [x] 2.2 Add `parse_tool_input(name, arguments_json)` helper (registry) — soft-fail, never raise to graph
- [x] 2.3 Implement `run_stuck_detector(state)` — unconditional fingerprint; auto-advance / replan-abort / WRAP_UP finish path per design; use `get_settings().PLANNER_AGENT_PHASE_STUCK_LIMIT`

## 3. Step 5.9 — agent + tool_executor

- [x] 3.1 Implement `agent_node` — max-tool ceiling → abort+WRAP_UP; `chat_with_tools` + nudge/`required` + synthesize default; `WandrLLMError` → default + `llm_retry_count`; never call `execute_tool`
- [x] 3.2 Implement `tool_executor_node` — `tool_context` from configurable only; loop pending → `execute_tool` → `apply_tool_result` → `maybe_transition_phase`; clear pending; full-list returns; stuck-detector every cycle
- [x] 3.3 Run step 5.9 ✅ import snippet; Select-String: zero tool-impl imports under `nodes/`; zero `execute_tool(` in `agent.py`

## 4. Step 5.10 — narrative + evaluation

- [x] 4.1 Implement `write_narrative` — `chat_completion` titles/paragraphs only; strip unknown place_ids; templates + `llm_retry_count` on `WandrLLMError`; never mutate stop order/times/coords
- [x] 4.2 Implement `EvaluationRepository` + `EvaluationService.record_generation(...)` mapping existing `TripEvaluation` columns (no migration)
- [x] 4.3 Implement `record_evaluation` node — short-lived session; DB fail → log + warning, no raise
- [x] 4.4 Run step 5.10 ✅ import snippet

## 5. Step 5.11 — graph compile

- [x] 5.1 Implement `build_planner_graph` / `get_compiled_graph` with locked edges (`parse_preferences` → agent → tool_executor unconditional; clarification END; plan_complete → narrative → evaluation → END; else → agent); singleton cache; no ToolContext closure
- [x] 5.2 Run step 5.11 ✅ compile snippet (`build_planner_graph()` returns compiled graph)

## 6. Verification + context

- [x] 6.1 Re-run 5.9–5.11 ✅ guards; spot-check existing pytest still green (`python -m pytest tests/ -v` or planner+core subset if slow)
- [x] 6.2 Update `docs/context.md`: Progress 5.9–5.11 ✅; Implemented modules for agent/tool_executor/narrative/evaluation nodes + builder + evaluation repo/service; Next step → 5.12; stubs list: remove those nodes/builder; keep PlannerService HTTP as P6 / 5.12+ stubs; note clarification evaluation deferred to 5.12 service
