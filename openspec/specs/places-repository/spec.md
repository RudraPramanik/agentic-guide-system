## Purpose

Place persistence via `PlaceRepository` — atomic OSM upsert, geography radius search, and destination-scoped list/count (flush-only; no HTTP).

## Requirements

### Requirement: Atomic place upsert from RawPOI

The system SHALL persist places via `PlaceRepository.upsert_from_poi(poi, destination_id)` using a single PostgreSQL `INSERT ... ON CONFLICT (osm_id) DO UPDATE ... RETURNING Place` statement. The repository MUST NOT use check-then-insert, MUST NOT issue a separate SELECT after upsert, and MUST NOT commit (flush/execute only; caller commits).

#### Scenario: Idempotent upsert same osm_id

- **WHEN** `upsert_from_poi` is called twice with the same `RawPOI.osm_id` and destination
- **THEN** both calls return the same `Place.id` and no duplicate row exists

#### Scenario: Conflict updates mutable fields

- **WHEN** a second upsert for the same `osm_id` supplies a new name, category, tags, location, or destination_id
- **THEN** the existing row is updated (including `updated_at`) and returned via RETURNING

#### Scenario: Repository does not commit

- **WHEN** `upsert_from_poi` succeeds
- **THEN** the session is not committed by the repository (caller may rollback and discard the row)

### Requirement: Geography-based radius search

The system SHALL implement `PlaceRepository.find_within_radius(lat, lng, radius_km, *, limit=100)` using `ST_DWithin` with **both** the place location and the query point cast to PostGIS `geography`, and distance `radius_km * 1000` (meters). Bare geometry degree comparisons MUST NOT be used. Soft-deleted places MUST be excluded. `ST_MakePoint` MUST receive `(longitude, latitude)`.

#### Scenario: Nearby point found within radius

- **WHEN** a place exists ~few hundred meters from `(lat, lng)` and `radius_km=5`
- **THEN** that place appears in the result list

#### Scenario: Distant point excluded

- **WHEN** the same place is queried with a center far outside `radius_km`
- **THEN** that place does not appear in the result list

### Requirement: Destination-scoped list and count

The system SHALL provide `list_by_destination(destination_id, params) -> tuple[list[Place], int]` by delegating to `BaseRepository.list_paginated` with `filters={"destination_id": destination_id}`, and `count_by_destination(destination_id) -> int` counting non-deleted places for that destination.

#### Scenario: Paginated list by destination

- **WHEN** at least one non-deleted place exists for a destination and `list_by_destination` is called with `PageParams(page=1, size=10)`
- **THEN** `total >= 1` and returned items belong to that destination

#### Scenario: Count excludes soft-deleted

- **WHEN** soft-deleted places exist for a destination
- **THEN** `count_by_destination` counts only rows where `deleted_at IS NULL`
