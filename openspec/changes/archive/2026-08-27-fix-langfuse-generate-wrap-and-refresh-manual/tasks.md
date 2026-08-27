## 1. Langfuse generate wrap

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and this change’s `design.md` / specs before coding
- [x] 1.2 In `PlannerService.generate`, call `start_generation_trace` after seeding initial state (fail-soft; include minimal metadata such as destination_id / session_id)
- [x] 1.3 Ensure timeout and recursion-abort branches still produce a final state dict usable for tool spans + outcome labeling
- [x] 1.4 After evaluation recording (always-run path / `finally`): `emit_tool_spans_from_trace(tool_trace)` then `end_generation_trace(outcome=..., metadata=...)` derived from terminal flags
- [x] 1.5 Confirm empty `LANGFUSE_*` still uses NoOp and generate return/evaluation path unchanged

## 2. Tests

- [x] 2.1 Extend `tests/planner/test_tracing_failsoft.py` (or sibling): mock lifecycle helpers; assert start once, end once, emit called with state’s `tool_trace` on success
- [x] 2.2 Assert end is still invoked on timeout / recursion-abort synthetic finals (patch graph to raise or return aborting state)
- [x] 2.3 Keep existing NoOp “generate completes” coverage; run `python -m pytest tests/planner/test_tracing_failsoft.py tests/planner -q` (or targeted subset) and fix failures

## 3. Junior developer manual catch-up

- [x] 3.1 Update `docs/app/documentation.md`: **Last refreshed**, **Through step** = P7 + V6.1 (or equivalent), recommended read order / snapshot no longer stuck at P6.5 / “next = P7.1”
- [x] 3.2 Refresh `docs/manual/03-module-map.md` and `04-imports-and-wiring.md` for P7 edit HTTP, evaluation flag polish, V2–V6.1 real modules; keep evaluation HTTP + `auth/dependencies.py` + deferred V6.2/V6.3 as stubs per context
- [x] 3.3 Refresh `docs/manual/05-how-to-change.md`: P7 smoke, optional `LANGFUSE_*`, `scripts/run_evals.py`; do not invent evaluation HTTP
- [x] 3.4 Touch `01-orientation.md` / `02-layers.md` only where they still claim pre-P7/v7 “next” or stub state
- [x] 3.5 Append catch-up row to `docs/manual/06-maintenance.md` refresh log

## 4. Light architecture / notes honesty

- [x] 4.1 Fix stale `docs/next_version.md` claim that `token_usage` is missing from `TravelState` (correct or mark historical/superseded by v2_blueprint V2)
- [x] 4.2 Minimal `docs/app/system.md` / `docs/app/lld.md` status fixes if they contradict post-P7 / V6.1 context (no architecture rewrite)
- [x] 4.3 Update `docs/context.md` Last updated + Langfuse/V2 wording so “trace around generate” matches the landed wrap; note manual refreshed through P7+V6.1 if the index marker changed

## 5. Proof / close-out

- [x] 5.1 Optional local proof (if keys available): one generate → Langfuse UI shows parent trace with nested tool + generation spans; unset keys → no Langfuse traffic — **skipped live UI** (keys empty in `.env`); NoOp + lifecycle covered by unit tests
- [x] 5.2 Confirm golden harness docs in the manual point at `run_evals` (no claim that Langfuse replaces pass_rate)
- [x] 5.3 Final pass: stubs in manual match `docs/context.md`; no new packages; no evaluation HTTP invented
