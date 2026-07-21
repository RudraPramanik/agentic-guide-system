## ADDED Requirements

### Requirement: Reorder day stops

The system SHALL expose `PATCH /api/v1/trips/{id}/days/{day}/stops/reorder` accepting ordered place_ids, re-running schedule and polyline for that day.

#### Scenario: Reorder updates times

- **WHEN** authenticated owner reorders day 1 stops
- **THEN** TripPlace order, suggested times, and GeoJSON reflect new order

### Requirement: Remove stop

The system SHALL expose `DELETE /api/v1/trips/{id}/days/{day}/stops/{place_id}` re-optimizing remaining day.

#### Scenario: Remove stop succeeds

- **WHEN** owner removes a stop from a valid day
- **THEN** stop is removed and day is re-routed

### Requirement: Add stop

The system SHALL expose `POST /api/v1/trips/{id}/days/{day}/stops` inserting at end with day load validation.

#### Scenario: Overloaded day rejected

- **WHEN** adding a stop would fail trip validation
- **THEN** response is 422 with validation details and trip unchanged

### Requirement: Reoptimize day

The system SHALL expose `POST /api/v1/trips/{id}/days/{day}/reoptimize` re-running route and schedule for one day.

#### Scenario: OSRM fail during reoptimize

- **WHEN** OSRM fails during reoptimize
- **THEN** haversine fallback is used and response is 200 not 500

### Requirement: Edit audit trail

Each edit operation SHALL write a `TripEditEvent` row and call `evaluation.service.record_edit()`.

#### Scenario: Edit creates audit row

- **WHEN** any P7 edit endpoint succeeds
- **THEN** TripEditEvent row exists with correct edit_type and payload snapshot
