## Context

See proposal.md for why this subslice exists. Specs: `specs/planner-runs/spec.md` and `specs/database-migrations/spec.md`.

The checkout has no `planner_runs` table. Migrations live under `migrations/versions/`. Current head is `a1b2c3d4e5f6`. `Trip` already stores a required `session_id` (`String(64)`) and an optional `user_id` FK to `users.id` with `ON DELETE SET NULL`. Pytest builds `wandr_test` with `Base.metadata.create_all` in `tests/conftest.py`. It does not run Alembic. There is no external call in this subslice, so no timeout, retry, or fallback is added.

## Goals / Non-Goals

**Goals:**

- One additive revision and a flush-only repository that satisfy the two delta specs.
- Uniqueness that matches an always-present session plus an optional user, without treating SQL `NULL` as a shared guest key.
- A migration test that does not stamp `alembic_version` onto `wandr_test`.

**Non-Goals:**

- A run service, status transition table, or `set_status` helper. `BaseRepository.update` stays the generic writer; subslice 1.2 is what G15 will later lock down.
- Computing `input_hash` or reading an idempotency header.
- A feature flag. Generate does not read `planner_runs`, so a flag would have nothing to switch.

## Decisions

### 1. Model follows Trip, and `id` is the run id

`PlannerRun` in `src/planner/runs/models.py` uses `Base`, `UUIDMixin`, and `TimestampMixin`. It does not use `SoftDeleteMixin`. The blueprint column `run_id` is this `id`. A second identifier would split the key 1.4 will return.

`RunStatus` is a `str` enum on that module, same pattern as `TripStatus`, with the eleven §6.7 values. The PostgreSQL type name is `run_status`. The column default is `accepted`.

Columns:

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID PK | no | mixin |
| `session_id` | `String(64)` | no | same limit as `trips.session_id` |
| `user_id` | UUID FK `users.id` `ON DELETE SET NULL` | yes | |
| `idempotency_key` | `String(128)` | no | stores a header or a hash; this row does not hash |
| `status` | enum `run_status` | no | default `accepted` |
| `input_hash` | `String(64)` | yes | filled in 1.3 |
| `trip_id` | UUID FK `trips.id` `ON DELETE SET NULL` | yes | |
| `failure_code` | `String(64)` | yes | |
| `workflow_version` | `String(64)` | yes | |
| `model_name` | `String(128)` | yes | attribute name avoids the Python `model` clash |
| `provider` | `String(64)` | yes | |
| `fallback_reason` | `String(255)` | yes | |
| `created_at`, `updated_at` | timestamp | no | mixin |

Alternative considered: a JSON blob for model/provider/fallback. Rejected because N10 records those three facts as separate values, and 1.1 has no writer that needs a document.

### 2. Two uniqueness rules, one of them partial

`UniqueConstraint(session_id, idempotency_key)` covers every row, because `session_id` is required.

A plain unique on `(user_id, idempotency_key)` does not mean "one row per user": PostgreSQL treats nulls as distinct, which is what we want for guests, but the constraint name would hide that. Use a partial unique index on `(user_id, idempotency_key) WHERE user_id IS NOT NULL` instead. Guests with the same key and different sessions both insert. The same user across two sessions does not.

Alternative considered: a generated owner column (`user_id` or else `session_id`). Rejected because it invents a third identity the trip model does not have.

### 3. Repository is BaseRepository plus two lookups

`PlannerRunRepository` subclasses `BaseRepository[PlannerRun, uuid.UUID]`. Inserts go through inherited `create`, which flushes and does not commit. Add `get_by_session_key` and `get_by_user_key` only. No transition method, no commit, no HTTP.

`src/planner/__init__.py` stays empty of a run import so importing the planner package does not require the model.

### 4. Hand-written revision, one env import

New file under `migrations/versions/`, `down_revision = "a1b2c3d4e5f6"`. Upgrade creates the `run_status` enum and `planner_runs` only. Downgrade drops the partial index, the table, and the enum, in that order. Do not autogenerate against the shared dev database; PostGIS tables make that noisy, and this revision is small enough to write by hand the way `20260728_a1b2c3d4e5f6_add_place_enriched_tags.py` was adjusted by hand.

`migrations/env.py` gains one import of `PlannerRun` next to the existing model imports. No other line in that file changes.

### 5. Tests split across create_all and a scratch database

`tests/planner/runs/conftest.py` imports `src.planner.runs.models` so collection registers the table before `test_engine` runs `create_all`. The root `tests/conftest.py` stays unchanged. Repository and HTTP tests use the existing `db_session` and `client` fixtures.

Uniqueness, default status, over-long keys, unknown status, unknown user, and rollback use `db_session`. Rollback is the fixture's own rollback: do not commit inside the repository test. User and trip delete tests hard-delete the parent row so `ON DELETE SET NULL` fires; soft-delete would not. Seed a `User` with `email` and `name`. Seed a trip the way `tests/trips/test_save_from_state.py` seeds a destination and places, without editing that file. The "save does not insert a run" test calls `TripService.save_from_state` and then counts `planner_runs`.

Migration tests MUST NOT run Alembic against `wandr_test`. Create and drop a scratch database (name ending in `_planner_runs_mig`) using the server from `get_settings().DATABASE_URL`. Point a subprocess `alembic` at that URL. Sequence: upgrade to `a1b2c3d4e5f6` and assert `planner_runs` is absent; `upgrade head`; `downgrade -1`; `upgrade head`; assert the seven older tables still exist. A second case upgrades an empty scratch database straight to head. Clear `get_settings` cache only inside the test process if the subprocess is not used. Prefer the subprocess so the pytest process keeps the dev URL.

The 404 scenario is `client.get("/api/v1/planner/runs/<uuid>")`.

### 6. No resilience wrapper

The repository talks only to the caller's `AsyncSession`. No httpx, tenacity, or named fallback.

## Risks / Trade-offs

- [Scratch migration test needs `CREATEDB` on the local Postgres role] → The compose database role already owns the dev database. If `CREATE DATABASE` fails, stop and report; do not point Alembic at `wandr` or `wandr_test`.
- [Nested conftest is skipped when pytest is aimed at another directory] → `pytest tests/planner/runs` and `pytest tests/` both load it. A trips-only run never needs this table.
- [`BaseRepository.update` can still write `status`] → 1.1 adds no status API. 1.2 introduces the only legal writer before G15 is enforced.
- [Partial unique index is PostgreSQL-specific] → The app database is Postgres. Do not add a second dialect.
- [Old app binary beside the new table] → Safe. Nothing in the request path selects `planner_runs` until 1.2.

## Migration Plan

1. Deploy the revision with `alembic upgrade head` before any later subslice writes rows. This subslice's application code does not write rows on the request path.
2. Rollback is `alembic downgrade -1` from the new head. That drops `planner_runs` and `run_status` only. There is no flag to flip.
3. Verify with the blueprint command against the scratch database, then `pytest tests/planner/runs -v`. Snapshot and architecture suites stay green because no route, event name, or `src/` behavior outside the new package changes.

## Open Questions

None. Idempotency-key format and whether a logged-in user's session key should also be checked at read time are 1.3 decisions. They do not change this table.
