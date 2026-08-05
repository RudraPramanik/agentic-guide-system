## Purpose

Trip repository and service persistence for P6.1 — exceptions, response schemas, Unit of Work `save_from_state`, ownership policy, and claim helpers. HTTP claim/CRUD/GeoJSON land in P6.3 (`trips-http-crud-geojson`); service helpers remain the policy source of truth.

## Requirements

### Requirement: Trip domain exceptions
The system SHALL implement `src/trips/exceptions.py` with `TripNotFoundError` (HTTP 404 via `NotFoundError`), `TripForbiddenError` (HTTP 403 via `ForbiddenError`), and `TripAlreadyClaimedError` (HTTP 409, `code="trip_already_claimed"`) for claim conflicts. Ownership misses MUST raise `TripForbiddenError`, never `TripNotFoundError`.

#### Scenario: Claim conflict is 409
- **WHEN** `TripAlreadyClaimedError` is raised
- **THEN** its `status_code` is 409 and `code` is `trip_already_claimed`

#### Scenario: Ownership miss is forbidden not not-found
- **WHEN** `assert_can_access` rejects a caller
- **THEN** it raises `TripForbiddenError` (403), not `TripNotFoundError`

### Requirement: Trip response schemas
The system SHALL implement `TripOut` and `TripPlaceOut` in `src/trips/schemas.py` covering existing Trip / TripPlace columns needed by list/get (including `suggested_start_time`, `visit_duration_min`, `polyline`) plus joined Place `lat`/`lng` (via PostGIS `to_shape`, same pattern as `PlaceOut`). Schemas MUST NOT invent columns absent from models.

#### Scenario: TripPlaceOut includes timing and geometry fields
- **WHEN** a `TripPlaceOut` is built from a loaded TripPlace + Place
- **THEN** it exposes `suggested_start_time`, `visit_duration_min`, `polyline`, `lat`, and `lng`

### Requirement: TripRepository list and eager get
The system SHALL implement `TripRepository(BaseRepository[Trip, UUID])` with:
- `list_by_user(user_id, params)` and `list_by_session(session_id, params)` returning paginated non-deleted trips
- `get_with_places(trip_id)` returning the trip with TripPlace rows and related Place eagerly loaded (coords available), or `None` if missing/soft-deleted

Repository writes MUST remain flush-only.

#### Scenario: get_with_places loads stops and place coords
- **WHEN** `get_with_places` is called for a saved trip with stops
- **THEN** the returned trip includes all TripPlace rows and each related Place is available for lat/lng extraction without additional queries per stop

#### Scenario: Soft-deleted trip is not returned
- **WHEN** `get_with_places` is called for a soft-deleted trip id
- **THEN** the result is `None`

### Requirement: TripService save_from_state Unit of Work
The system SHALL implement `TripService.save_from_state(state, user_id, session_id) -> Trip | None` that, in one transaction: creates the Trip, inserts all TripPlace rows from `state["schedule"]` day dicts, commits on success, and rolls back on any failure (no orphan Trip). Mapping MUST follow the locked v2 map: preferences from interests/budget/include_*; status COMPLETE/FAILED/DRAFT per plan_complete/abort_triggered; each stop’s `leg_polyline` → `TripPlace.polyline`. Return `None` when schedule is empty or the generation is clarification-only with nothing usable. `TripService` MUST NOT call `PlannerService`.

#### Scenario: Save then reload includes polylines
- **WHEN** `save_from_state` runs on a complete schedule whose stops include `leg_polyline`
- **THEN** the returned Trip is committed and `get_with_places` returns matching `TripPlace.polyline` values

#### Scenario: Partial insert rolls back
- **WHEN** a TripPlace insert fails mid-save
- **THEN** zero Trip rows remain committed for that attempt

#### Scenario: Clarification-only skips persist
- **WHEN** `save_from_state` is called with an empty schedule and `plan_complete` false / not a usable abort itinerary
- **THEN** the return value is `None` and no Trip row is created

### Requirement: Ownership and claim helpers
The system SHALL implement `TripService.assert_can_access(trip, *, user_id, session_id)` and `TripService.claim_for_user(trip, user_id, session_id) -> Trip`. Guest access requires exact `session_id` match. Authenticated access allows `trip.user_id == user_id` or (pre-claim) `trip.user_id is None` with matching session. Claim succeeds only when `trip.user_id is None` and session matches; otherwise `TripForbiddenError` or `TripAlreadyClaimedError`. Claim commits the updated `user_id`. HTTP claim and CRUD routes are delivered in step **6.3** (`trips-http-crud-geojson`); these service helpers remain the policy source of truth.

#### Scenario: Guest matching session may access unclaimed trip
- **WHEN** `user_id` is None and `session_id` equals `trip.session_id` on an unclaimed trip
- **THEN** `assert_can_access` returns without error

#### Scenario: Claim with matching session
- **WHEN** `claim_for_user` is called with matching session on `trip.user_id is None`
- **THEN** the trip’s `user_id` is set, committed, and returned

#### Scenario: Claim wrong session
- **WHEN** `claim_for_user` is called with a mismatched session
- **THEN** `TripForbiddenError` is raised and `trip.user_id` remains unchanged

#### Scenario: Re-claim conflict
- **WHEN** `claim_for_user` is called on a trip that already has `user_id` set
- **THEN** `TripAlreadyClaimedError` is raised

### Requirement: build_geojson from loaded trip
The system SHALL implement `TripService.build_geojson(trip) -> dict` that accepts a trip already loaded with places (and Place coords) and returns a GeoJSON FeatureCollection. It MUST emit Point features for stops and LineString features when `TripPlace.polyline` values decode; it MUST NOT perform network I/O or call `PlannerService`. Undecodable or None polylines MUST degrade to Points-only for affected legs/days without raising.

#### Scenario: Build includes Points
- **WHEN** `build_geojson` is called with a trip that has stops with Place coords
- **THEN** the FeatureCollection contains a Point feature per stop

#### Scenario: Build includes LineString when polyline present
- **WHEN** stops include decodable `polyline` values
- **THEN** the FeatureCollection contains at least one LineString feature

#### Scenario: None polylines do not raise
- **WHEN** all stop polylines are None
- **THEN** `build_geojson` returns a valid FeatureCollection of Points and does not raise

### Requirement: HTTP-facing service helpers
The system SHALL provide thin `TripService` helpers used by the 6.3 router: load-or-404 + ownership check for get/delete, paginated list for the authenticated user, soft-delete with commit, and claim wrapper that loads then calls `claim_for_user`. Repository remains flush-only except where existing BaseRepository soft_delete patterns apply; service owns commit for mutating helpers.

#### Scenario: Get missing trip is 404
- **WHEN** get helper is called for an unknown or soft-deleted trip id
- **THEN** it raises `TripNotFoundError`

#### Scenario: Soft delete commits
- **WHEN** soft-delete helper succeeds for an owned trip
- **THEN** subsequent `get_with_places` returns None for that id
