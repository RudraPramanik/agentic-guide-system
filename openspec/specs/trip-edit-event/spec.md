## Purpose

Append-only audit model for user-initiated trip edits (P7). Links to evaluation quality signals via `record_edit()`.

## Requirements

### Requirement: EditType enum defines four edit kinds

The system SHALL define `EditType` as a string enum with values: `reorder`, `remove_stop`, `add_stop`, `reoptimize_day`.

#### Scenario: Enum values match P7 contract

- **WHEN** `EditType` is imported from `src.trips.models`
- **THEN** all four blueprint edit types are present

### Requirement: TripEditEvent model maps to trip_edit_events table

The system SHALL provide `TripEditEvent` with columns: `id` (UUID PK), `trip_id` (FK trips CASCADE), `edit_type` (edit_type enum), `day_number` (nullable int), `place_id` (nullable FK places SET NULL), `payload` (JSONB, default `{}`), `created_at`, `updated_at`.

#### Scenario: Model has no soft delete

- **WHEN** `TripEditEvent` class is inspected
- **THEN** it does not inherit `SoftDeleteMixin` and has no `deleted_at` column

### Requirement: Composite index for trip timeline queries

The system SHALL define index `ix_trip_edit_events_trip_created` on `(trip_id, created_at)`.

#### Scenario: Index present after migration

- **WHEN** migration 003 is applied
- **THEN** index exists on `trip_edit_events(trip_id, created_at)`

### Requirement: P1 smoke script verifies TripEditEvent CASCADE

The P1 smoke script SHALL insert a `TripEditEvent`, verify read-back, delete the parent trip, confirm CASCADE removal, and roll back the transaction.

#### Scenario: Smoke test covers edit events

- **WHEN** `python scripts/test_p1_smoke.py` runs after step 1.12
- **THEN** output includes a passed TripEditEvent section
