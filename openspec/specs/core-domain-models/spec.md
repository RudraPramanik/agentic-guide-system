## Purpose

Core SQLAlchemy domain models for users, destinations, places, trips, and evaluation.

## Requirements

### Requirement: User model matches auth schema

The system SHALL define a `User` SQLAlchemy model at `src/auth/models.py` with mixins `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` and columns: `email`, `name`, `avatar_url`, `google_id`, `is_active`.

#### Scenario: User table columns present

- **WHEN** `User.__table__.columns` is inspected
- **THEN** columns include `id`, `email`, `name`, `google_id`, `is_active`, `deleted_at`, `created_at`, `updated_at`

### Requirement: Destination model tracks readiness counters

The system SHALL define `Destination` at `src/destinations/models.py` without `SoftDeleteMixin`, with geocode fields and denormalized counters `place_count`, `enriched_count`, `indexed_count`.

#### Scenario: Destination counter columns

- **WHEN** `Destination.__table__.columns` is inspected
- **THEN** columns include `place_count`, `enriched_count`, `indexed_count`, `lat`, `lng`, `country`, `display_name`

### Requirement: Place model uses PostGIS POINT geometry

The system SHALL define `Place` with `location` as `Geometry(geometry_type="POINT", srid=4326)` and FK `destination_id` → `destinations.id` ON DELETE CASCADE.

#### Scenario: Place geometry column

- **WHEN** `Place.__table__.columns` is inspected
- **THEN** a `location` column exists and composite index `ix_places_destination_category` is defined

### Requirement: Trip and TripPlace model trip itinerary stops

The system SHALL define `TripStatus` str enum, `Trip` with nullable `user_id`, required `session_id`, JSONB `preferences`, and `TripPlace` with day ordering, timing fields, and `UniqueConstraint(trip_id, place_id)`.

#### Scenario: TripPlace uniqueness and timing columns

- **WHEN** `TripPlace.__table__.columns` and constraints are inspected
- **THEN** columns include `order_in_day`, `suggested_start_time`, `polyline` and unique constraint on `(trip_id, place_id)` exists

### Requirement: TripEvaluation captures full generation observability

The system SHALL define append-only `TripEvaluation` with all blueprint fields including `tool_trace`, `abort_triggered`, resilience flags, and quality signals — minimum 28 columns, no soft delete.

#### Scenario: TripEvaluation required columns

- **WHEN** `TripEvaluation.__table__.columns` is inspected
- **THEN** all fields from step 1.4c validation set are present including `tool_loop_count`, `used_geo_fallback`, `validation_warnings`

### Requirement: No ORM relationships in step 1.4 models
Models from step 1.4 originally MUST NOT define `relationship()` until both sides exist. As of step **6.1**, `Trip`, `TripPlace`, and `Place` MAY define SQLAlchemy `relationship()` mappings solely to support eager loading in `TripRepository.get_with_places` (and later GeoJSON/schema mapping). Relationships MUST NOT introduce new columns or require an Alembic migration. Other domain models MAY remain relationship-free until a later step needs them.

#### Scenario: Trip eager-load relationships exist for 6.1
- **WHEN** `Trip` / `TripPlace` models are inspected after step 6.1
- **THEN** relationships exist so `get_with_places` can selectinload places and Place without N+1 queries

#### Scenario: No schema migration for relationships
- **WHEN** relationships are added for Trip/TripPlace/Place
- **THEN** no new table columns are introduced and no Alembic revision is required for this change

### Requirement: Trips domain includes TripEditEvent audit model

The trips domain models module SHALL export `EditType` and `TripEditEvent` in addition to `TripStatus`, `Trip`, and `TripPlace`.

#### Scenario: Import trip edit types

- **WHEN** code executes `from src.trips.models import TripEditEvent, EditType`
- **THEN** import succeeds without error

#### Scenario: TripEditEvent repr is debug-friendly

- **WHEN** `repr(TripEditEvent(...))` is called
- **THEN** output includes id, trip_id, and edit_type
