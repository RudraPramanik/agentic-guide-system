## 1. Author P7 Cursor build contract (this change — docs only)

- [x] 1.1 Write `docs/steps/step7.md` as the canonical P7 contract (mirror structure of `docs/steps/step5.md` / `step6.md`): header with blueprint SoT v6.1 §P7, layering note, gate = P6.5 green in `docs/context.md`
- [x] 1.2 Include Decision / Fix Log covering design locks: P5 REPLAN ≠ P7 HTTP; no PlannerService/`execute_tool`; base_lat/lng in preferences + destination fallback; reorder preserves order (no `optimize_route`); remove/add/reoptimize use `optimize_route`; score=1.0 hydrate; empty day 422; validate_trip → 422 rollback; OSRM fail-soft 200; require_auth + ownership; TripEditEvent + record_edit
- [x] 1.3 Include Prerequisites, prompt conventions, AGENT guardrails reminder, P7 architecture ASCII (HTTP → TripService → travel_engine + RoutingProvider → UoW + TripEditEvent)
- [x] 1.4 Include Shared locks sections: auth matrix (four edit routes), failure-mode table, abstraction/provider swap table, design patterns, code quality / system design principles, forward locks (chat replan / eval HTTP = post-P7)
- [x] 1.5 Write pasteable prompts for **7.0** (persist base in preferences + `_resolve_base`), **7.1** (service edit ops + schemas + FAILURE BOUNDARY), **7.2** (router + rate limits), **7.3** (pytest), **7.4** (`record_edit`), **7.5** (smoke + context.md) — each with ✅ validation and ✅ Failure path
- [x] 1.6 End with P7 ship criteria table + Recommended OpenSpec implementation batches: `7.0` → `7.1` → `7.2` → `7.3` → `7.4` → `7.5` as **separate** code applies after this planning change
- [x] 1.7 Confirm `openspec validate --change design-p7-edit-replan` (or status) reports artifacts complete

## 2. Principle / coherence checks (docs only)

- [x] 2.1 Spot-check step7 forbids: LLM on edit path, `execute_tool` / LangGraph on edit, Redis imports in trips router, raw dict responses, `os.environ.get`, inventing endpoints beyond blueprint four
- [x] 2.2 Spot-check blueprint alignment: four paths, `ApiResponse[TripOut]`, require_auth + ownership, validation 422 rollback, OSRM haversine fallback, TripEditEvent + evaluation linkage
- [x] 2.3 Do **not** mark P7 ✅ in `docs/context.md` in this change (implementation not started)

## 3. Hand-off for later code implementation (tracking only)

- [x] 3.1 Document in step7 Recommended batches that code apply order is 7.0→7.5 and must not start until this planning change’s `step7.md` exists
- [x] 3.2 After archive, sync delta specs (`p7-trip-edit-replan`, `p7-edit-evaluation`, `trips-repository-service`) to main via `/opsx:sync` or archive workflow — do not hand-edit `openspec/specs/` outside that workflow
