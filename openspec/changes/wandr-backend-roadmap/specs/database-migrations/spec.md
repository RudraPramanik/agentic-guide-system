## ADDED Requirements

### Requirement: Migration 003 for trip edit events

The system SHALL include Alembic revision 003 creating `trip_edit_events` table and index on `trip_id`.

#### Scenario: Head includes edit events table

- **WHEN** `alembic upgrade head` runs on a database at revision 002
- **THEN** revision 003 applies and `trip_edit_events` is visible in psql

## MODIFIED Requirements

### Requirement: Core domain migrations are sequential

The system SHALL maintain ordered Alembic revisions: 001 PostGIS extensions, 002 six core tables, 003 trip_edit_events.

#### Scenario: Fresh database bootstrap

- **WHEN** migrations run from empty database
- **THEN** all three revisions apply in order without error
