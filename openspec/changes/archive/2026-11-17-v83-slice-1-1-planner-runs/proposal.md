## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **1.1**, and §8.1) starts Slice 1 with an additive `planner_runs` record so later subslices can attach idempotency and terminal status without changing generate behavior first. There is no `docs/steps/step*.md` for this work. Subslices 0.1–0.5 are archived. The S0 audit records `planner_runs` as absent (`docs/v8.2/repository_audit.md`). `docs/context.md` does not mention the table and is not the source for this row.

## What Changes

- Add an additive Alembic revision that creates `planner_runs` and drops only that table on downgrade. Head today is revision `a1b2c3d4e5f6`.
- Add a SQLAlchemy model and a flush-only repository under `src/planner/runs/`. The primary key is the existing `UUIDMixin.id`. That value is the run id. There is no second `run_id` column.
- Persist the §8.1 fields: owner (`session_id` required, `user_id` optional), `idempotency_key`, `status`, `input_hash`, optional `trip_id`, `failure_code`, timestamps, `workflow_version`, and nullable model / provider / fallback text.
- Enforce uniqueness of `(session_id, idempotency_key)` and, when `user_id` is set, `(user_id, idempotency_key)`.
- Register the model in `migrations/env.py` so autogenerate follows the existing `database-migrations` spec.
- No **BREAKING** changes. No HTTP, SSE, or planner-service change.

## Capabilities

### New Capabilities

- `planner-runs`: additive `planner_runs` table, model, and repository. Insert is flush-only. Duplicate owner+key inserts fail. No status machine and no HTTP API.

### Modified Capabilities

- `database-migrations`: the next revision creates `planner_runs` with a working downgrade, and `migrations/env.py` imports the new model.

## Impact

- **Work surface:** `migrations/versions/**`, `src/planner/runs/**`, `tests/planner/runs/**`, plus the one existing import line in `migrations/env.py`.
- **No new package.** No `requirements.txt` change. No external I/O, so no new timeout or retry.
- **No impact on:** `POST /planner/generate`, SSE event names, trip save, snapshots, settings, or `docs/context.md`.
- **Downstream:** 1.2 owns status transitions, 1.3 owns the idempotency key and the save guard, 1.4 owns `GET /api/v1/planner/runs/{run_id}`.

## Non-goals

- No run lifecycle service, no transition table, and no writes from `src/planner/service.py` (subslice 1.2).
- No client idempotency header, no request hash function, and no change to `TripService.save_from_state` (subslice 1.3).
- No `GET` or cancel route, no `docs/FE_guide.md` edit, and no SSE `run_id` field (subslice 1.4).
- No `RUN_TRACKING_ENABLED` setting. Nothing reads a flag in this subslice. `src/config.py` and `.env.example` stay untouched. Rollback for 1.1 is `alembic downgrade -1`.
- No checkpoint, resume, lease, or worker.
- No edit to `docs/context.md`. Row 1.1's allowed paths forbid it, the same way Slice 0 left that file alone. The §19 completion report goes in the PR description.
- No ADR-006. That record covers idempotency scope and belongs with 1.3, when behavior can conflict with the preference cache.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay on Router → Service → Repository. This row adds a repository only. No router and no service.
- Keep LLM, geo, and `travel_engine` untouched. The repository does not call the network.
- Add no package and no env read. Status values live on the model enum, the same way `TripStatus` does.
- Keep the migration additive: no `ALTER` or `DROP` of existing application tables.

Blueprint path notes, confirmed against the checkout rather than treated as a halt:

- §9 names `alembic/versions/`. The repo's migration root is `migrations/versions/` (audit and revisions `001`, `4251bc619373`, `6e0f01af33c5`, `a1b2c3d4e5f6`). Use the real directory.
- The row requires tests and the locked migration spec requires an `env.py` import. Those two files sit outside the literal path cell: `tests/planner/runs/**` and a single import in `migrations/env.py`. No other file outside `src/planner/runs/**` and `migrations/versions/**` is in scope. The model is imported from `tests/planner/runs/conftest.py` so pytest `create_all` sees the table without editing the root harness.
