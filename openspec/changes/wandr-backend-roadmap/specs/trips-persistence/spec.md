## ADDED Requirements

### Requirement: Save trip from agent state

The system SHALL persist Trip and TripPlace rows atomically via `TripService.save_from_state()` in one transaction.

#### Scenario: Rollback on partial failure

- **WHEN** any TripPlace insert fails during save
- **THEN** entire transaction rolls back and no orphan Trip exists

### Requirement: Trips CRUD endpoints

The system SHALL expose authenticated list, get, delete, and GeoJSON export for trips with ownership checks returning 403 on mismatch.

#### Scenario: GeoJSON renders route

- **WHEN** `GET /api/v1/trips/{id}/geojson` is called for a saved trip
- **THEN** response is valid GeoJSON FeatureCollection with route geometry

### Requirement: Anonymous trip claim

The system SHALL allow trips created with session_id to be linked to user after login when session matches.

#### Scenario: Login claims guest trip

- **WHEN** authenticated user had same session_id as guest trip creator
- **THEN** trip user_id is updated to authenticated user
