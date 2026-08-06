## 1. Setup

- [x] 1.1 Read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.5 before coding
- [x] 1.2 Grep for callers of `mark_user_edited` / `mark_trip_edited` (expect evaluation service + TripService UoW only)

## 2. Repository + service polish

- [x] 2.1 Extend `EvaluationRepository`: add `get_latest_for_trip(trip_id) -> TripEvaluation | None` (order by `created_at` desc, limit 1)
- [x] 2.2 Change `mark_user_edited` to accept `evaluation: TripEvaluation`, set `user_edited=True`, flush only, return the row; remove trip_id-based combined helper
- [x] 2.3 Polish `EvaluationService.mark_trip_edited(trip_id)`: get latest → no-op if missing or already `user_edited` → else `mark_user_edited(evaluation)`; docstring MUST state flag-only / no TripEditEvent / no LLM
- [x] 2.4 Confirm TripService `_persist_day_and_audit` still calls `mark_trip_edited` after `insert_edit_event` and before commit (same session); no call-site change unless broken

## 3. Tests

- [x] 3.1 Add `tests/evaluation/test_mark_trip_edited.py` (or equivalent): edit/call path with evaluation → `user_edited` True
- [x] 3.2 Missing evaluation → `mark_trip_edited` no-op (does not raise); successful edit still produces `TripEditEvent` when exercised via TripService
- [x] 3.3 Spy/assert: invoking `mark_trip_edited` alone inserts zero `trip_edit_events` rows
- [x] 3.4 Already-`user_edited` latest row → no-op without error
- [x] 3.5 Run `python -m pytest tests/evaluation/ -v` (and any touched trips tests) → green; then `python -m pytest tests/ -v` → green (248 passed)

## 4. Context checkpoint

- [x] 4.1 Update `docs/context.md`: Last updated, Progress 7.5 ✅, Next → 7.6, Current state (evaluation flag polish), Implemented modules note for locked `get_latest_for_trip` / flag-only `mark_trip_edited`; stubs: evaluation HTTP still stub
- [x] 4.2 Do not implement evaluation HTTP, migrations, or 7.6 smoke in this change
