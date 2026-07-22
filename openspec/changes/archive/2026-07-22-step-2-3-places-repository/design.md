## Context

P2.2 is done: `RawPOI` + `fetch_pois`. `Place` model (unique `osm_id`, PostGIS POINT 4326, soft-delete) and `BaseRepository` (flush-only, `list_paginated`, `_soft_delete_filter`) exist. `src/places/repository.py` is a one-line stub. Canonical source: `docs/steps/step2.md` §2.3 (v2 — geography locked, atomic RETURNING upsert, runnable validation). No step-doc amendment required.

## Goals / Non-Goals

**Goals:**
- Real `PlaceRepository` with `upsert_from_poi`, `find_within_radius`, `list_by_destination`, `count_by_destination`
- Single atomic `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` (concurrency-safe, one round trip)
- Radius search always via `geography` cast + meters (`radius_km * 1000`)
- Soft-delete aware reads; flush-only writes (caller commits)
- Pass step 2.3 validation scripts; bump `docs/context.md` → Next **2.6a**

**Non-Goals:**
- Seed script (2.4), DestinationRepository (2.6b), places HTTP (2.7), OSRM (2.5)
- Pytest module `tests/places/` (2.9)
- New packages or migrations
- Clearing / restoring `deleted_at` on upsert (not in step; defer if seed needs resurrect)

## Decisions

### D1 — Implement step 2.3 as written (no step amendment)
- **Locked:** `ST_MakePoint(lng, lat)` order; geography cast both sides; RETURNING (no SELECT-back); repository never commits.
- **Alt rejected:** Amending step2.md — v2 already fixed race, units, and validation snippets.

### D2 — Upsert maps `RawPOI.raw_tags` → `Place.tags`
- Column is `tags` (JSONB); DTO field is `raw_tags`. Match step snippet exactly.
- `updated_at=func.now()` only on conflict update set (not on insert values — TimestampMixin / DB default covers create).

### D3 — Soft-delete filter on reads only
- `find_within_radius` and `list_by_destination` / `count_by_destination` use `_soft_delete_filter()` (or equivalent `deleted_at IS NULL`).
- Upsert does **not** set `deleted_at`; soft-deleted rows with the same `osm_id` remain soft-deleted after ON CONFLICT update until a later step needs resurrect. Acceptable for P2.3 (seed creates new rows).

### D4 — `list_by_destination` delegates to `list_paginated`
- `filters={"destination_id": destination_id}` + `PageParams` — reuse BaseRepository pagination (default `created_at` desc).

### D5 — `count_by_destination` is a thin COUNT
- `select(func.count()).select_from(Place).where(destination_id=..., deleted_at IS NULL)` — used by seed (2.4) for `place_count`. No pagination.

### D6 — Failure boundary
- DB errors propagate to caller (seed will log + continue per POI in 2.4).
- Must not: commit inside repo; swallow `IntegrityError`; check-then-insert.

### D7 — Validation session factory
- Use existing `AsyncSessionLocal()` from `src.core.database.session` (callable returning session CM). Scripts need live Postgres + migrations applied; rollback at end.

## Risks / Trade-offs

- [Soft-deleted + same osm_id upsert] → Row updates but stays invisible to radius/list → document; fix in later step if seed needs resurrect
- [True multi-session concurrent insert] → Same-session double call in validation proves ON CONFLICT shape; real races still safe under unique `osm_id` + ON CONFLICT
- [Geography cast CPU cost] → Correctness over bare geometry; P2 volumes (~150 POIs/dest) fine
- [Validation needs Docker Postgres] → Same as P1 smoke; no new infra

## Migration Plan

1. Implement `src/places/repository.py`
2. Run step 2.3 happy-path + concurrent-style validation (`python -c "..."`)
3. Update `docs/context.md` (2.3 ✅, Next → 2.6a, Implemented modules, stubs)
4. No Alembic — schema already present

## Open Questions

- None blocking. Soft-delete resurrect on upsert deferred unless seed (2.4) surfaces the need.
