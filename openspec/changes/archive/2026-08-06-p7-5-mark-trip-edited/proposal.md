## Why

P7.2 shipped a thin `EvaluationService.mark_trip_edited` so TripService UoW could call the final name; repo helper still takes `trip_id` and always sets the flag. Step **7.5** (`docs/steps/step7.md`) locks the full flag-only contract — split lookup vs mutate, skip already-edited rows, prove edit-with / edit-without evaluation + zero `TripEditEvent` inserts — so AGENT.md “evaluation records every edit” is honored without evaluation owning audit events.

## What Changes

- Extend `EvaluationRepository` with `get_latest_for_trip(trip_id)` and flush-only `mark_user_edited(evaluation)` (sets `user_edited=True` on the given row).
- Polish `EvaluationService.mark_trip_edited(trip_id)` to: load latest → no-op if missing or already `user_edited` → else mark; still never creates `TripEditEvent`, no LLM/planner.
- Confirm TripService already calls `mark_trip_edited` after `TripEditEvent` insert in the same UoW (no call-site change expected).
- Add focused tests for the three step-7.5 validation scenarios (flag set; no-eval edit still 200 + event; spy zero edit-event inserts from `mark_trip_edited`).
- Update `docs/context.md` after validation (Progress 7.5 ✅, Next → 7.6).

**Non-goals:** Evaluation HTTP routes; new `TripEvaluation` columns / migrations; creating `TripEditEvent` inside EvaluationService; smoke script / P7 close-out (7.6); changing TripService day-surgery semantics or edit HTTP surface; PlannerService / `execute_tool` / LLM on edit path; new packages.

**Naming note:** Blueprint historically named this `record_edit`; v2.1 delta is `mark_trip_edited` flag-only with TripService owning `TripEditEvent`. Build from `docs/steps/step7.md` §7.5.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `p7-edit-evaluation`: Replace the 7.2 “thin/acceptable” wording with the locked 7.5 API — `get_latest_for_trip` + evaluation-arg `mark_user_edited`; service skips when already flagged; explicit validation scenarios for with/without evaluation and zero event inserts.

## Impact

- **Code:** `src/evaluation/repository.py`, `src/evaluation/service.py`; tests under `tests/evaluation/` and/or extension of `tests/trips/test_edit_replan.py`; TripService wire already present (`_persist_day_and_audit`).
- **Docs:** `docs/context.md` after green (Next → 7.6); stubs note that evaluation HTTP remains stub.
- **AGENT.md:** evaluation reflects every edit; Router→Service→Repository; no LLM on edit path; TripService owns audit event.
- **Depends on:** P7.2–7.4 (edit UoW + routes + `test_edit_replan` matrix).
- **Unlocks:** 7.6 smoke (optional) + P7 context close-out.
- **No DB migration / no new packages / no new live endpoints.**
