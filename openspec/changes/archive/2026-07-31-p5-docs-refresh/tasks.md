## 1. Context gate + developer manual index

- [x] 1.1 Confirm Through-step target from `docs/context.md` (prefer P5.14 + Next P6.1 after sibling `step-5-12-5-14` smoke/context closeout; if context still lags, Through-step ≤ highest ✅ P5 step — do not claim unfinished modules)
- [x] 1.2 If context still lists Next as P5.12–5.14 but those modules are already validated green, bump `docs/context.md` Progress / Implemented / Stubs / Next → P6.1 to match truth (docs-only; no inventing HTTP generate)
- [x] 1.3 Bump `docs/app/documentation.md` to Through step **P5.14** (or gated target), refresh date, read-order “next” hint (P6.1), and snapshot (P5 tools/orchestration/graph/eval/service bridge + pytest tool-loop + `scripts/test_agent.py`; stubs = trips HTTP + planner HTTP)
- [x] 1.4 Add P5 phase-complete / catch-up row to `docs/manual/06-maintenance.md` refresh log; update “next natural refresh” to the next cadence trigger

## 2. Module map, layers, wiring, recipes

- [x] 2.1 Update `docs/manual/03-module-map.md` through P5: mark planner tools/orchestration/graph nodes/builder, evaluation repo/service, PlannerService bridge, `tests/planner/test_tool_loop.py`, `scripts/test_agent.py` as real when context says ✅; keep trips HTTP, `/planner/generate`, `auth/dependencies.py` stub-explicit
- [x] 2.2 Update `docs/manual/04-imports-and-wiring.md` for P5 agent↔tool_executor loop, bookends, compiled graph, ToolContext via configurable, optional emit → PlannerService (remove “lands in P5” wording where shipped)
- [x] 2.3 Update `docs/manual/05-how-to-change.md` with P5 verification recipes (`pytest tests/planner`, `scripts/test_agent.py`); explicitly note `/planner/generate` is not live yet
- [x] 2.4 Skim `docs/manual/01-orientation.md` and `02-layers.md` for stale “planner LangGraph stub / next is P5.1” claims; fix only factual drift

## 3. P2 study guide + architecture light touch

- [x] 3.1 Update `docs/app/p2guide.md` “still stubs / next phase” framing: planner graph/tools real; next = P6.1; keep P2 teaching body and formula-true readiness floors
- [x] 3.2 Scan `docs/app/system.md` and `docs/app/lld.md` for concrete post-P5 factual drift (planner “future P5”, pattern table still upcoming); apply minimal corrections only (no architecture rewrite)

## 4. Sanity check

- [x] 4.1 Run the `06-maintenance.md` sanity checklist against `docs/context.md` (implemented vs stubs; no stub API recipes; no invented `/planner/generate` live route)
- [x] 4.2 Confirm no doc under `docs/app/` or `docs/manual/` still claims P5 planner graph/tools are unbuilt, or that next build step is P5.1
