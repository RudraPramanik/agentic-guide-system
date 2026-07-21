## ADDED Requirements

### Requirement: Migration 003 creates trip_edit_events table

Migration 003 SHALL create `trip_edit_events` with `edit_type` PostgreSQL enum and foreign keys: `trip_id` → `trips.id` ON DELETE CASCADE, `place_id` → `places.id` ON DELETE SET NULL.

#### Scenario: Seventh table after upgrade

- **WHEN** `alembic upgrade head` completes after migration 003
- **THEN** `\dt` lists seven application tables including `trip_edit_events`

#### Scenario: edit_type enum exists

- **WHEN** querying `pg_type` for `edit_type`
- **THEN** exactly one row is returned

#### Scenario: Migration is additive only

- **WHEN** migration 003 file is reviewed before apply
- **THEN** it contains no ALTER or DROP on the six existing application tables from migration 002

## MODIFIED Requirements

### Requirement: Model imports are registered in alembic env

`alembic/env.py` MUST import each domain `models.py` so autogenerate sees `Base.metadata` tables. New models MUST be added to this import block when created.

#### Scenario: TripEditEvent registered for autogenerate

- **WHEN** `alembic/env.py` is loaded
- **THEN** `TripEditEvent` is imported from `src.trips.models` alongside `Trip`, `TripPlace`, `TripStatus`
