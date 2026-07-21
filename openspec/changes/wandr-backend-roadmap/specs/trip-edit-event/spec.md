## ADDED Requirements

### Requirement: TripEditEvent table exists after migration 003

The system SHALL persist trip edit audit rows in `trip_edit_events` with columns: `id`, `trip_id`, `edit_type` (reorder | remove_stop | add_stop | reoptimize_day), `day_number`, `place_id`, `payload` (JSONB before/after), `created_at`.

#### Scenario: Migration applies cleanly

- **WHEN** `alembic upgrade head` runs after migration 002
- **THEN** table `trip_edit_events` exists with index on `trip_id`

### Requirement: TripEditEvent model is importable

The system SHALL expose `TripEditEvent` in `src/trips/models.py` using SQLAlchemy 2.0 `Mapped[]` style and blueprint mixins.

#### Scenario: Model import

- **WHEN** code imports `TripEditEvent` from `src.trips.models`
- **THEN** no import error and model maps to `trip_edit_events` table
