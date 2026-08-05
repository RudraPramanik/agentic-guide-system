## Purpose

Trips FastAPI HTTP surface for P6.3 — CRUD, public GeoJSON FeatureCollection, and claim after login. Builds on trips repository/service (P6.1) and polyline persistence from generate (P6.2).

## Requirements

### Requirement: Trips HTTP auth matrix and registration
The system SHALL register `src/trips/router.py` on the FastAPI app with prefix `/api/v1/trips` and expose exactly these 6.3 endpoints (no P7 edit routes):

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/` | `require_auth` | `PaginatedResponse[TripOut]` |
| GET | `/{id}` | `optional_auth` + ownership | `ApiResponse[TripOut]` |
| GET | `/{id}/geojson` | public | GeoJSON FeatureCollection (not `ApiResponse`) |
| DELETE | `/{id}` | `require_auth` + ownership | HTTP 204 |
| POST | `/{id}/claim` | `require_auth` + session match + unclaimed | `ApiResponse[TripOut]` |

Router MUST call `TripService` only (never repository/DB). DELETE asymmetry vs guest GET MUST be commented in code as intentional (no anonymous destructive actions). Soft-delete MUST use `BaseRepository.soft_delete`.

#### Scenario: Trips routes registered including claim
- **WHEN** the app is created after step 6.3
- **THEN** route paths include trips list/get/geojson/delete and `claim`

#### Scenario: List requires authentication
- **WHEN** an unauthenticated client calls `GET /api/v1/trips`
- **THEN** the API returns 401

#### Scenario: Guest get with matching session
- **WHEN** an unauthenticated client with `wandr_session` equal to `Trip.session_id` calls `GET /api/v1/trips/{id}`
- **THEN** the API returns 200 with `ApiResponse` data `TripOut`

#### Scenario: Ownership miss is 403 not 404
- **WHEN** a client requests another user's trip or a guest session mismatches
- **THEN** the API returns 403 (`TripForbiddenError`), not 404

#### Scenario: Anonymous delete forbidden
- **WHEN** an unauthenticated client calls `DELETE /api/v1/trips/{id}`
- **THEN** the API returns 401

### Requirement: Public GeoJSON FeatureCollection from persisted data
The system SHALL implement `TripService.build_geojson(trip)` and `GET /api/v1/trips/{id}/geojson` that returns a GeoJSON `FeatureCollection` built only from already-loaded TripPlace / Place fields (no live OSRM, httpx, or `src/geo` network calls on read).

The collection MUST include a Point feature per stop with coordinates from Place geometry and properties including at least name, day, order, and `suggested_start_time` when present. When encoded `TripPlace.polyline` values decode successfully, the collection MUST include LineString feature(s) for that geometry (prefer per-day concatenation of leg polylines). A day/trip with all-None or undecodable polylines MUST still return valid Point features and MUST NOT raise (expected OSRM-down degradation). Missing/soft-deleted trip MUST 404. GeoJSON MUST NOT be wrapped in `ApiResponse`.

#### Scenario: LineString present when polylines persisted
- **WHEN** geojson is requested for a trip whose stops have decodable polylines
- **THEN** the body is a FeatureCollection containing at least one LineString and Point features for stops

#### Scenario: Points-only degradation without polylines
- **WHEN** geojson is requested for a trip whose stop polylines are all None
- **THEN** the body is a valid FeatureCollection with Point features and no LineString requirement failure / no 500

#### Scenario: Geojson does not call routing
- **WHEN** `build_geojson` runs
- **THEN** it performs no OSRM/httpx/network I/O

### Requirement: Claim HTTP endpoint
The system SHALL expose `POST /api/v1/trips/{id}/claim` with `require_auth`. The handler MUST read `wandr_session`, load the trip, and call `TripService.claim_for_user` (or equivalent service wrapper). Success returns `ApiResponse[TripOut]` with `user_id` set. Session mismatch MUST surface as 403; already-claimed as 409 (`trip_already_claimed`); missing trip as 404. Router MUST NOT catch these with ad-hoc try/except — use the global WandrError handler.

#### Scenario: Claim succeeds after login
- **WHEN** an authenticated user posts claim with `wandr_session` matching an unclaimed trip
- **THEN** response is 200 and the trip’s `user_id` equals that user

#### Scenario: Claim wrong session
- **WHEN** claim is posted with a non-matching session cookie
- **THEN** response is 403 and `user_id` remains null

#### Scenario: Re-claim conflict
- **WHEN** claim is posted for a trip that already has `user_id` set
- **THEN** response is 409 with code `trip_already_claimed`
