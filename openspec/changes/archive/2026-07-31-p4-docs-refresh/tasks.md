## 1. Developer manual index + maintenance

- [x] 1.1 Bump `docs/app/documentation.md` to Through step **P4.10**, refresh date, read-order “next” hint (P5.1), and snapshot (P3 search/enrich/index + live `search_available`; P4 travel_engine + CORS + OsrmRoutingProvider + tools envelope; pytest + `scripts/test_p4_smoke.py`; next = P5.1)
- [x] 1.2 Add P3+P4 catch-up / P4 phase-complete row to `docs/manual/06-maintenance.md` refresh log; update “next natural refresh” to the next cadence trigger

## 2. Module map, layers, wiring, recipes

- [x] 2.1 Update `docs/manual/03-module-map.md` through P4.10: mark `search/*`, enrich/index scripts, CORS, all `travel_engine/*`, `planner/routing_provider`, `ToolResult`/`execute_tool` envelope, `tests/search|travel_engine|planner`, `scripts/test_p4_smoke.py` as real; keep planner LangGraph / tool bodies, trips/evaluation beyond models, `auth/dependencies.py` stub-explicit
- [x] 2.2 Update `docs/manual/04-imports-and-wiring.md` for P3 search/enrich wiring and P4 travel_engine + routing-provider DI + tools envelope (remove “lands later” wording where those are shipped)
- [x] 2.3 Update `docs/manual/05-how-to-change.md` with enrich/index + P4 smoke/pytest recipes; note live `search_available`; preserve formula-true readiness floors
- [x] 2.4 Skim `docs/manual/01-orientation.md` and `02-layers.md` for stale “P3 incomplete / search|travel_engine stub / next is P3.1” claims; fix only factual drift

## 3. P2 study guide + architecture light touch

- [x] 3.1 Update `docs/app/p2guide.md` “still stubs / next phase” framing: search + travel_engine are real; next = P5.1; keep P2 teaching body and formula-true readiness floors
- [x] 3.2 Scan `docs/app/system.md` and `docs/app/lld.md` for concrete post-P4 factual drift; apply minimal corrections only (no architecture rewrite)

## 4. Sanity check

- [x] 4.1 Run the `06-maintenance.md` sanity checklist against `docs/context.md` (implemented vs stubs; no stub API recipes; no invented P5 graph/tool body APIs)
- [x] 4.2 Confirm no doc under `docs/app/` or `docs/manual/` still claims P3/P4 modules are unbuilt, or that next build step is P3.1 / P4
