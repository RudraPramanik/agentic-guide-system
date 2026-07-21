## Why

P1 step 1.8 (request logging) is complete; `docs/context.md` marks **Next step: 1.9**. The `TripEditEvent` audit table is required before P7 edit/replan endpoints and before `evaluation.service.record_edit()` can link user edits to quality signals. Adding the model and migration now avoids a schema change mid-planner work.

## What Changes

- Add `EditType` enum and `TripEditEvent` model to `src/trips/models.py` (append-only audit; no `SoftDeleteMixin`).
- Register `TripEditEvent` in `alembic/env.py` model imports.
- Generate and apply **Alembic migration 003** — `trip_edit_events` table + `edit_type` enum + composite index on `(trip_id, created_at)`.
- Update `docs/context.md` — step 1.9 ✅, next step 1.10.

**Non-goals (step 1.9 only):**

- No repository, service, or router for edit events (P7).
- No `record_edit()` implementation (P7 / evaluation service).
- No API endpoints.
- No new packages.

## Capabilities

### New Capabilities

- `trip-edit-event`: SQLAlchemy model + DB schema for append-only trip edit audit rows.

### Modified Capabilities

- `database-migrations`: Add migration 003 requirement for `trip_edit_events` table.
- `core-domain-models`: Register `TripEditEvent` and `EditType` in trips domain models.

## Impact

| Area | Impact |
|------|--------|
| `src/trips/models.py` | New `EditType`, `TripEditEvent` |
| `alembic/env.py` | Import `TripEditEvent` |
| `alembic/versions/` | New revision 003 |
| Database | 7th application table; FK cascade to `trips`, SET NULL on `places` |
| Runtime API | None — schema-only step |
