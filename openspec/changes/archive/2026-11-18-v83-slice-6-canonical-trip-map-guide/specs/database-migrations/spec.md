## ADDED Requirements

### Requirement: Trips gain version and trip places gain status and provenance
An Alembic revision MUST add `trips.version` as a non-null integer with server default 1, and MUST backfill existing rows to 1. It MUST add `trip_places.stop_status` as a non-null string enum of `confirmed`, `suggested`, `removed`, and `user_added`, with server default `confirmed`, and MUST backfill existing rows to `confirmed`. It MUST add nullable `trip_places.geometry_provenance` limited to `osrm`, `haversine_estimate`, and `none`. It MUST NOT drop or retype `polyline`, `order_in_day`, `place_id`, or the unique constraint on `(trip_id, place_id)`. Downgrade MUST drop only `trips.version`, `trip_places.stop_status`, and `trip_places.geometry_provenance`.

#### Scenario: Upgrade adds the columns
- **WHEN** `alembic upgrade head` runs
- **THEN** `trips.version` exists and is non-null, `trip_places.stop_status` exists, and `trip_places.geometry_provenance` exists and is nullable

#### Scenario: Existing stops stay confirmed
- **WHEN** upgrade runs against a database that already has trip places
- **THEN** those rows have `stop_status=confirmed` and `version=1` on their trip, and their polyline and order are unchanged

#### Scenario: Downgrade removes only the new columns
- **WHEN** `alembic downgrade -1` runs after that upgrade
- **THEN** those three columns are gone and the unique `(trip_id, place_id)` constraint remains
