## Why

Step 1.3 enabled PostGIS and Alembic, but the database has no application tables yet. Steps **1.4a–1.4d** (`docs/steps/step1.md`) define six core SQLAlchemy models and migration 002 — the schema foundation for auth, destinations, places, trips, and evaluation before repositories (1.5) and domain services.

## Readiness verdict

**Ready to implement 1.4a → 1.4c now.** Step specs are largely correct and align with `docs/blueprint_final.md` TripEvaluation schema and existing mixins in `src/core/database/base.py`.

**1.4d needs two Alembic prep fixes** not in the step doc (discovered during exploration):

1. Add `alembic/script.py.mako` — autogenerate fails without it (`FileNotFoundError`).
2. Add `include_object` filter in `alembic/env.py` — on PostGIS Docker images, bare autogenerate detects ~40 Tiger/system tables and generates **DROP** operations for tables not in `Base.metadata`.

**Minor step-doc fixes** (implement correctly; optional doc patch later):

- **1.4b:** `trips/models.py` snippet uses `Text` for `TripPlace.polyline` but omits `Text` from imports.
- **Step 1.1 rules (line ~94):** says Trip does not use `SoftDeleteMixin`; **1.4b gives Trip with SoftDeleteMixin** — follow 1.4b (soft-delete trips is correct for BaseRepository in 1.5).

## What Changes

### 1.4a — User + Destination
- Implement `src/auth/models.py` (User)
- Implement `src/destinations/models.py` (Destination)
- Register imports in `alembic/env.py`

### 1.4b — Place + Trip + TripPlace
- Implement `src/places/models.py` (Place with PostGIS POINT SRID 4326)
- Implement `src/trips/models.py` (TripStatus enum, Trip, TripPlace)
- Register imports in `alembic/env.py`

### 1.4c — TripEvaluation
- Implement `src/evaluation/models.py` (TripEvaluation — 28+ columns per blueprint)
- Register import in `alembic/env.py`

### 1.4d — Migration 002
- Add `alembic/script.py.mako` + `include_object` in env.py
- `alembic revision --autogenerate -m "create_all_tables"`
- Manual review checklist (Geometry not VARCHAR, trip_status enum, indexes, no spurious DROPs)
- `alembic upgrade head`
- psql validation (`\dt`, `\di`, `trip_status` type)

### Non-goals
- TripEditEvent (step 1.9 / migration 003)
- Repositories, services, routers, relationships
- New pip packages (geoalchemy2 already installed in 1.3)

## Capabilities

### New Capabilities
- `core-domain-models`: SQLAlchemy models for User, Destination, Place, Trip, TripPlace, TripEvaluation
- `database-migrations`: Delta to step 1.3 — migration 002 create-all-tables + autogenerate safety

### Modified Capabilities
- `database-migrations` (from step 1.3 change): add script template, include_object filter, migration 002 requirements

## Impact

| Area | Effect |
|------|--------|
| **Files** | 5 `models.py` stubs → real code; `alembic/env.py` imports; new `script.py.mako`; migration 002 |
| **Dependencies** | None new — uses sqlalchemy, geoalchemy2 from 1.3 |
| **APIs** | None |
| **DB** | 6 new tables + trip_status enum + PostGIS spatial index on places.location |
| **Prerequisites** | Step 1.3 ✅; bare `DATABASE_URL` in `.env`; Docker Postgres on 5433 |
