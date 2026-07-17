## ADDED Requirements

### Requirement: Alembic autogenerate template exists

The project SHALL include `alembic/script.py.mako` so `alembic revision --autogenerate` can generate migration files.

#### Scenario: Autogenerate succeeds

- **WHEN** `alembic revision --autogenerate -m "create_all_tables"` runs with all models imported
- **THEN** a new revision file is created without `FileNotFoundError` for script.py.mako

### Requirement: Autogenerate ignores non-application tables

Alembic env SHALL configure `include_object` to skip autogenerate DROP operations for database tables not present in `Base.metadata` (PostGIS/Tiger system tables).

#### Scenario: No spurious DROP operations

- **WHEN** autogenerate runs against PostGIS Docker Postgres before migration 002
- **THEN** the generated migration contains CREATE operations for application tables only, not DROP of Tiger/geocoder tables

### Requirement: Migration 002 creates six application tables

Migration 002 SHALL create `users`, `destinations`, `places`, `trips`, `trip_places`, `trip_evaluations` with correct types and constraints per step 1.4d review checklist.

#### Scenario: Tables exist after upgrade

- **WHEN** `alembic upgrade head` completes after migration 002
- **THEN** `\dt` lists all six tables and `trip_status` enum type exists

#### Scenario: PostGIS geometry in migration

- **WHEN** migration 002 is reviewed before running
- **THEN** `places.location` uses Geometry type, not VARCHAR or Text
