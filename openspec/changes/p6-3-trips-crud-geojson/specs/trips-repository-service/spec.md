## ADDED Requirements

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

## MODIFIED Requirements

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
