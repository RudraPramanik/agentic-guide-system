## Context

**Built so far:** Six core tables (migration 002), `Trip` / `TripPlace` in `src/trips/models.py`, async Alembic env with model imports.

**Blueprint ref:** P1 step 1.9 — `docs/steps/step1.md` § Step 1.9, `docs/blueprint_final.md` TripEditEvent schema.

**Purpose of TripEditEvent:** Append-only audit log for P7 edits (`reorder`, `remove_stop`, `add_stop`, `reoptimize_day`). Links to `TripEvaluation.user_edited` via `evaluation.service.record_edit()` in a later step.

## Goals / Non-Goals

**Goals:**

- Model matches step 1.9 prompt exactly (columns, FKs, index, enum).
- Migration 003 is additive only — no changes to existing six tables.
- Validation passes: 7 tables, `edit_type` enum in `pg_type`.

**Non-Goals:**

- Repository CRUD, API, or evaluation wiring.

## Decisions

### D1 — No SoftDeleteMixin on TripEditEvent

**Decision:** Use `UUIDMixin` + `TimestampMixin` only.

**Rationale:** Audit rows are append-only and never soft-deleted (step 1.9 docstring + blueprint).

### D2 — place_id FK ondelete SET NULL

**Decision:** `ForeignKey("places.id", ondelete="SET NULL")`.

**Rationale:** Preserve edit history even if a place row is removed later.

### D3 — trip_id FK ondelete CASCADE

**Decision:** Deleting a trip removes its edit events.

**Rationale:** Orphan audit rows have no meaning without the parent trip.

### D4 — Composite index (trip_id, created_at)

**Decision:** `Index("ix_trip_edit_events_trip_created", "trip_id", "created_at")`.

**Rationale:** P7/evaluation will query edits per trip chronologically.

### D5 — Autogenerate then review

**Decision:** Use `alembic revision --autogenerate -m "add_trip_edit_events"`, manually verify checklist before `upgrade head`.

**Rationale:** Matches P1 convention; catches accidental diffs on existing tables.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Autogenerate touches existing tables | Review migration file; reject if any ALTER on tables 001–002 |
| Enum name collision | Use `edit_type` enum name per step prompt; verify `\d trip_edit_events` |
| Missing env.py import | TripEditEvent not in metadata → empty autogenerate; checklist in tasks |

## Migration Plan

1. Add model to `trips/models.py`
2. Update `alembic/env.py` import
3. Autogenerate → review → `alembic upgrade head`
4. Run psql validation from step1.md
5. Update `docs/context.md`

## Open Questions

- None — step 1.9 prompt is fully specified.
