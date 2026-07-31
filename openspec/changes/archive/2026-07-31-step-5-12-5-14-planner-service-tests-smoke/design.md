## Context

P5.1–5.11 are done: 12-tool registry, orchestration, `TravelState`, agent↔executor loop, narrative/eval bookends, and `get_compiled_graph()` singleton. `src/planner/service.py` remains a step-0.1 stub. Clarification paths end at END without the graph `record_evaluation` node (deferred from 5.9–5.11). Emit hooks are not yet wired — `tool_executor` does not checkpoint state for a service-level timeout.

This batch implements **5.12–5.14** from `docs/steps/step5.md` / `docs/blueprint_final.md` v6.1 (OpenSpec cluster 5 — final P5 batch). Guardrails: `AGENT.md`.

## Goals / Non-Goals

**Goals:**

- Ship `PlannerService.generate` with fresh `ToolContext` per invoke, configurable `emit`, `asyncio.wait_for` ceiling, and `last_known_state` outside the cancellable task
- Persist evaluation for timeout + clarification short-circuits (and any path that never hit the graph eval node)
- Ship `tests/planner/test_tool_loop.py` with all locked ★ cases
- Ship `scripts/test_agent.py` smoke + mark P5 complete in `docs/context.md` after green

**Non-Goals:**

- FastAPI `POST /planner/generate` StreamingResponse, SSE `asyncio.Queue`, disconnect cancel (**P6**)
- Trips CRUD / guest claim / save_from_state (**P6**)
- New packages or TripEvaluation migrations
- Rewiring clarification through in-graph narrative (keep 5.11 edges)

## Decisions

1. **Service owns the timeout boundary** — `generate` builds initial `TravelState` + `ToolContext(routing=OsrmRoutingProvider(), db=None, …)` **fresh every call**. Invokes `get_compiled_graph().ainvoke(initial, config={"configurable": {"tool_context": ctx, "emit": _capture_and_emit}})` inside `asyncio.wait_for(..., timeout=get_settings().PLANNER_GENERATION_TIMEOUT_SECONDS)`.
   - Alternative: timeout inside a graph node — **rejected**; cancelled task must not be the only source of final state (Decision Log #15).

2. **`last_known_state` lives outside the wait_for task** — mutable dict closed over by `_capture_and_emit`. On each emit with `state_snapshot`, `clear()` + `update(snapshot)` (shallow dict copy of TravelState-compatible keys). On `TimeoutError`: `final = {**last_known_state, "errors": … + ["generation_timeout"], "abort_triggered": True}` and emit `error` / `generation_timeout`. Never assume cancelled `ainvoke` return value is usable.

3. **Emit is optional and config-injected** — nodes read `emit = config["configurable"].get("emit")`. If missing (unit tests / direct graph invoke), no-op. **Minimum wiring:** `tool_executor_node` calls `emit("tool_done", {…}, state_snapshot=working_state)` after each successful `apply_tool_result` cycle (at least once per pending batch / per tool). Prefer also emitting after the full pending batch + stuck-detector so snapshot includes phase transitions. Do not close over `generate` locals at **compile** time — only pass callable via configurable per invoke.

4. **Evaluation after generate** — Follow step 5.12: after timeout **or** normal return, service MUST ensure evaluation is recorded.
   - **Resolve double-write vs clarification gap:** Call `record_evaluation(final)` (the existing node / shared helper) when **any** of: timeout path; `needs_clarification=True`; `abort_triggered` without having completed the narrative bookend; OR always call and accept a second analytics row on happy path.
   - **Locked choice for apply:** Always call service-level `await record_evaluation(final)` as in the step snippet (ALWAYS). Happy-path may insert two `TripEvaluation` rows (graph node + service) — acceptable for P5 append-only analytics; do not add dedupe logic in this batch.
   - Clarification/timeout that never reached the graph node still get a row — satisfies the deferred 5.11 lock.

5. **No HTTP in this batch** — Do not register `planner/router` or claim `/planner/generate` live. Service `on_event` callback is the bridge P6 will feed into an SSE queue.

6. **Tests use mocks + FakeRoutingProvider** — `test_tool_loop.py` mocks `chat_with_tools` / `chat_completion`; inject Fake routing via ToolContext; seed minimal destination/places only when a case needs DB/search, otherwise mock tool results / phase machine. Concurrent isolation test: two `asyncio.gather(generate(...))` with different `destination_id` against the **same** cached compiled graph — assert each ctx sees its own destination (spy ToolContext or tool args).

7. **Smoke is sectioned and fail-loud** — `scripts/test_agent.py` prints numbered section headers; `sys.exit(1)` on first failure; never print ambiguous ALL PASSED. Prefer `PlannerService.generate` (no HTTP). Requires seeded+enriched+indexed Darjeeling + LLM keys — document in script header.

8. **context.md last** — Update only after `python scripts/test_agent.py` and `python -m pytest tests/ -v` green. Next step → P6.1; stubs keep trips CRUD + planner HTTP router.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Timeout cancels before any emit → empty eval | Require ≥1 tool cycle before timeout in tests; emit after first tool apply; smoke/docs note empty last_known is still recorded with timeout error |
| Double TripEvaluation on happy path | Accepted P5; document in context/service docstring; P6 may tighten |
| Concurrent generate shares graph but leaks ctx | Fresh ToolContext per invoke via configurable only; concurrent test is merge gate |
| Emit signature drift vs P6 SSE event names | Use simple `(event: str, data: dict, state_snapshot=None)`; P6 maps to SSE event types |
| Live smoke flaky without seed/LLM | Fail loud with section header; do not mark context P5 complete if smoke fails |
| Implementer registers HTTP generate early | Explicit non-goal + assert in 5.14 checklist that path not registered |

## Migration Plan

1. Wire optional `emit` into `tool_executor_node` (delta)
2. Implement `PlannerService.generate` + step 5.12 ✅ snippet
3. Add `tests/planner/test_tool_loop.py` ★ cases; run planner + full pytest
4. Add `scripts/test_agent.py`; run smoke
5. Update `docs/context.md` (5.12–5.14 ✅, Next = P6.1)
6. Rollback: revert `service.py` to stub + remove emit calls / new tests/script; no DB migration

## Open Questions

- None blocking. Double-evaluation on happy path is an explicit accepted trade-off; amend step5 only if product forbids duplicate eval rows before apply.
