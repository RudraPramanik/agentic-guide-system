## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.7, §8.1, and §9 row 1.1, plus this change's `proposal.md`, `design.md`, and both delta specs. There is no `docs/steps/step*.md` for this row.
- [x] 1.2 Confirm writes stay inside `src/planner/runs/**`, `migrations/versions/**`, `tests/planner/runs/**`, and one import in `migrations/env.py`. Do not edit `src/config.py`, `src/planner/service.py`, `src/trips/service.py`, `src/planner/router.py`, `tests/conftest.py`, or `docs/context.md`.

## 2. Model and repository

- [x] 2.1 Add `src/planner/runs/models.py` with `RunStatus` (the eleven §6.7 values) and `PlannerRun` (`UUIDMixin` + `TimestampMixin`, no soft delete). Primary key `id` is the run id. Columns and nullability match design Decision 1, including `model_name`.
- [x] 2.2 Add the session unique constraint and the partial unique index `WHERE user_id IS NOT NULL` from design Decision 2. Foreign keys use `ON DELETE SET NULL`.
- [x] 2.3 Add `PlannerRunRepository` extending `BaseRepository`, with inherited flush-only `create` plus `get_by_session_key` and `get_by_user_key`. Do not add a status-transition method or a commit.

## 3. Migration

- [x] 3.1 Add a hand-written revision under `migrations/versions/` with `down_revision = "a1b2c3d4e5f6"`. Upgrade creates enum `run_status` and table `planner_runs` only. Downgrade drops the partial index, the table, and the enum.
- [x] 3.2 Import `PlannerRun` in `migrations/env.py` next to the existing model imports. Change no other line in that file.

## 4. Tests

- [x] 4.1 Add `tests/planner/runs/conftest.py` that imports `src.planner.runs.models` so `create_all` sees `planner_runs`. Do not edit the root harness.
- [x] 4.2 Add repository tests for default status `accepted`, rejected status `running`, session-key duplicate, same key on another session, user-key duplicate across sessions, over-long `session_id` or `idempotency_key`, unknown `user_id`, rollback hiding the row, and hard-delete of the user or trip leaving the run with a null reference.
- [x] 4.3 Add a test that `TripService.save_from_state` inserts no `planner_runs` row, and a test that `GET /api/v1/planner/runs/{run_id}` returns 404.
- [x] 4.4 Add a scratch-database migration test (name ending in `_planner_runs_mig`). Do not run Alembic against `wandr` or `wandr_test`. Assert upgrade to `a1b2c3d4e5f6` has no `planner_runs`, then `upgrade head` / `downgrade -1` / `upgrade head`, and assert the seven older application tables remain. Also assert an empty database upgraded to head creates `planner_runs`. If `CREATE DATABASE` fails, stop and report.

## 5. Verify

- [x] 5.1 Run `pytest tests/planner/runs -v` and confirm exit 0.
- [x] 5.2 Run `pytest tests/snapshots tests/architecture -q` and confirm those suites stay green.
- [x] 5.3 Confirm the diff is only the paths in task 1.2. No `requirements.txt` edit, no flag, no HTTP route, no `docs/context.md` edit. Put the blueprint §19 completion report in the PR description.
