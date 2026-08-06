## Why

P7.0–7.5 are green in `docs/context.md` (edit ops, four HTTP routes, `test_edit_replan`, flag-only `mark_trip_edited`), but the phase is not closed until Step **7.6** (`docs/steps/step7.md`) runs the ship gate: full pytest green, optional live smoke, edit-path import guards, and a P7-complete `docs/context.md` stamp — only after those checks pass. Without this close-out, agents may still treat P7 as in-progress or stamp context prematurely.

## What Changes

- Optionally add `scripts/test_p7_smoke.py`: owned trip → reorder day 1 → assert exactly one `TripEditEvent`; GeoJSON shows polyline when present. Prefer offline Fake; live OSRM optional behind an env flag.
- Spot-check import guards: trips edit modules must not import `litellm`, `langgraph`, `PlannerService`, `execute_tool`, or `redis`.
- Run `python -m pytest tests/trips/test_edit_replan.py -v` and `python -m pytest tests/ -v`; only then update `docs/context.md` to P7 complete (7.0–7.6 ✅, Next → post-P7 / production readiness).
- Context stamp fields locked by step 7.6: current state (day edit/replan HTTP + TripEditEvent; shared polyline helper; preserve-order reorder); implemented modules (edit methods, routes, `rate_limit_trip_edit`, `mark_trip_edited`, `populate_leg_polylines`, preserve-order schedule); four live edit endpoints; known MVP limitation (concurrent edits last-write-wins); clear “P7 trip edit/replan HTTP still stubs”; do **not** claim evaluation HTTP done.

**Non-goals:** F1 chat replan; marking roadmap / production-readiness items done; new edit endpoints or TripService semantics; evaluation HTTP; new packages; Alembic migrations; inventing DayPlan/ScheduledStop polyline fields; PlannerService / `execute_tool` / LLM on edit path; mandatory developer-manual rewrite in this change (phase-end manual refresh may follow as a separate docs change per `docs/manual/06-maintenance.md`).

**Naming note:** Build from `docs/steps/step7.md` §7.6. Smoke is optional; context.md update is mandatory and blocked on failed pytest (and on failed smoke if the script is present).

## Capabilities

### New Capabilities

- `p7-ship-verification`: P7.6 ship gate — optional `scripts/test_p7_smoke.py`, edit-path import guards, full pytest green, and `docs/context.md` P7-complete stamp only after green.

### Modified Capabilities

- (none — edit/replan behavior already locked under `p7-trip-edit-replan`, `p7-edit-evaluation`, `p7-edit-replan-tests`; this change verifies and documents, it does not change those requirements)

## Impact

- **Code (optional):** `scripts/test_p7_smoke.py` if written; no production module changes expected.
- **Docs:** `docs/context.md` after green (Progress 7.0–7.6 ✅, Next → post-P7 / production readiness).
- **Tests:** Re-run `tests/trips/test_edit_replan.py` + full suite; smoke if present.
- **AGENT.md:** Router→Service→Repository; no LLM / planner tools / litellm / langgraph on edit path; travel_engine purity; `ApiResponse[T]`; context.md only after validated step.
- **Depends on:** P7.0–7.5 complete (context already shows 7.5 ✅).
- **Unlocks:** post-P7 / production readiness work; optional separate developer-manual refresh through P7.6.
- **No DB migration / no new packages / no new live endpoints.**
