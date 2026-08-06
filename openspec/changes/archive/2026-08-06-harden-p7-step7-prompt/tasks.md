## 1. Author hardened step7.md SoT

- [x] 1.1 Replace `docs/steps/step7.md` with full **v2.1** Cursor build contract (style of `step5.md` / `step6.md`): header stating OpenSpec change `harden-p7-step7-prompt`, supersedes v1 / critics file is historical only, blueprint delta callouts, naming trap (P5 REPLAN ≠ P7 HTTP)
- [x] 1.2 Write Decision/Fix Log covering locks from `design.md` D1–D9 (event ownership, safe shared polylines, parallel polyline persist, preserve-order reorder, no silent drops, zero-network other days, permutation/404/rate-limit/concurrency)
- [x] 1.3 Write Shared locks sections: auth matrix, failure-mode table (v2.1), abstraction/provider swap, design patterns, code-quality principles, forward locks (F1 chat replan, F2 eval HTTP, F3 row locking, F4 base columns, F5 further day-surgery extract)
- [x] 1.4 Author pasteable steps **7.0–7.6** with EXTEND/ADD/FAILURE BOUNDARY/DO NOT/✅ Validation/✅ Failure path each:
  - 7.0 base prefs + `_resolve_base`
  - 7.1 promote shared polyline helper; keep full pairwise `OptimizeResult.legs`
  - 7.2 TripService edits + preserve-order schedule + drop/polyline/audit locks
  - 7.3 router + `rate_limit_trip_edit` (add 429 exception if missing)
  - 7.4 `tests/trips/test_edit_replan.py` including v2.1 regressions
  - 7.5 `mark_trip_edited` flag-only
  - 7.6 optional smoke + `docs/context.md` (code-ship only)
- [x] 1.5 Add P7 ship criteria table + recommended OpenSpec implementation batch list (`7.0`→`7.6`); note minimal replan during code apply only when feature reality conflicts — amend step7 then code

## 2. Verify contract against specs and design

- [x] 2.1 Spot-check step7.md against `specs/p7-trip-edit-replan/spec.md` (HTTP, drop rejection, preserve-order, morning downgrade, audit ownership)
- [x] 2.2 Spot-check against `specs/p7-edit-evaluation/spec.md`, `travel-engine-route-optimizer`, `travel-engine-schedule-builder`, `trips-repository-service` deltas
- [x] 2.3 Confirm step7 explicitly forbids: inventing DayPlan/ScheduledStop polyline fields; replacing OptimizeResult.legs with consecutive-only; EvaluationService creating TripEditEvent; PlannerService/execute_tool/LLM on edit path
- [x] 2.4 Confirm `docs/step7_critics.md` is referenced as historical review only (not SoT)

## 3. Docs hygiene (this change only)

- [x] 3.1 Do **not** mark P7 code Progress ✅ in `docs/context.md` (code not implemented yet); optionally note Next step still points at P7 and step7.md is now v2.1 SoT only if a one-line clarification helps — prefer leaving context Progress unchanged until 7.6 code ship
- [x] 3.2 Run `openspec status --change harden-p7-step7-prompt` and confirm apply-ready artifacts remain complete after step7 rewrite
