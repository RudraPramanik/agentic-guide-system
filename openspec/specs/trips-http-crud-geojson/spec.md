## Purpose

Trips FastAPI HTTP surface for P6.3 — CRUD, public GeoJSON FeatureCollection, and claim after login. Builds on trips repository/service (P6.1) and polyline persistence from generate (P6.2).

## Requirements

### Requirement: Trips HTTP auth matrix and registration
The system SHALL register `src/trips/router.py` on the FastAPI app with prefix `/api/v1/trips` and expose the P6.3 CRUD/GeoJSON/claim endpoints **plus** the P7.3 day-scoped edit endpoints:

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/` | `require_auth` | `PaginatedResponse[TripOut]` |
| GET | `/{id}` | `optional_auth` + ownership | `ApiResponse[TripOut]` |
| GET | `/{id}/geojson` | public | GeoJSON FeatureCollection (not `ApiResponse`) |
| DELETE | `/{id}` | `require_auth` + ownership | HTTP 204 |
| POST | `/{id}/claim` | `require_auth` + session match + unclaimed | `ApiResponse[TripOut]` |
| PATCH | `/{id}/days/{day}/stops/reorder` | `require_auth` + owner + `rate_limit_trip_edit` | `ApiResponse[TripOut]` |
| DELETE | `/{id}/days/{day}/stops/{place_id}` | `require_auth` + owner + `rate_limit_trip_edit` | `ApiResponse[TripOut]` |
| POST | `/{id}/days/{day}/stops` | `require_auth` + owner + `rate_limit_trip_edit` | `ApiResponse[TripOut]` |
| POST | `/{id}/days/{day}/reoptimize` | `require_auth` + owner + `rate_limit_trip_edit` | `ApiResponse[TripOut]` |

Router MUST call `TripService` only (never repository/DB). DELETE asymmetry vs guest GET MUST remain commented in code as intentional (no anonymous destructive actions). Soft-delete MUST use `BaseRepository.soft_delete`. Edit routes MUST NOT use `optional_auth`. P6.3 route behavior MUST remain unchanged aside from coexistence with the new edit paths.

#### Scenario: Trips routes registered including claim and edits
- **WHEN** the app is created after step 7.3
- **THEN** route paths include trips list/get/geojson/delete, `claim`, and the four day-scoped edit endpoints

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

#### Scenario: Edit routes reject optional guest auth
- **WHEN** an unauthenticated client calls any of the four edit endpoints
- **THEN** the API returns 401 (not 403-via-guest-session)

### Requirement: Public GeoJSON FeatureCollection from persisted data
The system SHALL implement `TripService.build_geojson(trip)` and `GET /api/v1/trips/{id}/geojson` that returns a GeoJSON `FeatureCollection` built only from already-loaded TripPlace / Place fields (no live OSRM, httpx, or `src/geo` network calls on read).

While `CANONICAL_TRIP_V2_ENABLED` is false, the collection MUST include a Point feature per persisted stop with coordinates from Place geometry and properties including at least name, day, order, and `suggested_start_time` when present. When encoded `TripPlace.polyline` values decode successfully, the collection MUST include LineString feature(s) for that geometry (prefer per-day concatenation of leg polylines). Properties MUST NOT include `geometry_provenance`.

While `CANONICAL_TRIP_V2_ENABLED` is true, Point features MUST be emitted only for rows whose `stop_status` is `confirmed` or `user_added`. `suggested` and `removed` rows MUST NOT appear as points or as legs of a line. A LineString for a day MUST be emitted only when every routed leg on that day has `geometry_provenance=osrm` and the polyline decodes. That LineString's properties MUST include `day`, `trip_id`, and `geometry_provenance` equal to `osrm`. A day whose provenance is `haversine_estimate` or `none` MUST contribute points only.

A day/trip with all-None or undecodable polylines MUST still return valid Point features for the stops included by the flag rule above and MUST NOT raise (expected OSRM-down degradation). Missing/soft-deleted trip MUST 404. GeoJSON MUST NOT be wrapped in `ApiResponse`. The geometry types MUST remain Point and LineString only.

#### Scenario: LineString present when polylines persisted
- **WHEN** geojson is requested for a trip whose stops have decodable polylines and the flag is false
- **THEN** the body is a FeatureCollection containing at least one LineString and Point features for stops, and no feature property is named `geometry_provenance`

#### Scenario: Points-only degradation without polylines
- **WHEN** geojson is requested for a trip whose stop polylines are all None
- **THEN** the body is a valid FeatureCollection with Point features and no LineString requirement failure / no 500

#### Scenario: Geojson does not call routing
- **WHEN** `build_geojson` runs
- **THEN** it performs no OSRM/httpx/network I/O

#### Scenario: Flag on hides suggestions and labels an OSRM line
- **WHEN** the flag is true and a day has one confirmed stop with provenance `osrm` and one suggested stop
- **THEN** the collection has a point only for the confirmed stop and, when that day's routed polylines all decode as `osrm`, the line property `geometry_provenance` is `osrm`

#### Scenario: Flag on haversine day has no line
- **WHEN** the flag is true and every routed stop on a day has provenance `haversine_estimate`
- **THEN** that day contributes points only and no LineString

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

### Requirement: Flag-on trip JSON carries status, provenance, and version
While `CANONICAL_TRIP_V2_ENABLED` is true, `TripOut` MUST include `version` and each `TripPlaceOut` MUST include `stop_status` and `geometry_provenance`. The `places` array MUST include `suggested` and `removed` rows as well as routed rows so the client sees one id space. While the flag is false, those three keys MUST be absent and `places` MUST remain the persisted routed rows only. List and get envelopes MUST stay `PaginatedResponse` and `ApiResponse`. No new trip path is added.

#### Scenario: Flag on get includes the new keys
- **WHEN** an owner fetches `GET /api/v1/trips/{id}` with the flag true
- **THEN** `data.version` is an integer and each place includes `stop_status` and `geometry_provenance`

#### Scenario: Flag off get matches the frozen shape
- **WHEN** a client fetches the same route with the flag false
- **THEN** the trip JSON has no `version`, `stop_status`, or `geometry_provenance` key

### Requirement: Edit routes return 409 on a stale version
The four existing day-edit routes MUST, when `CANONICAL_TRIP_V2_ENABLED` is true, enforce the trip version in `canonical-trip-identity`. A mismatch MUST be HTTP 409 code `trip_version_conflict` via the global error handler, and the body MUST NOT be a successful `ApiResponse`. The paths, auth, and rate limit MUST stay as they are today. While the flag is false, a version header MUST NOT change the status code relative to today's edit rules.

#### Scenario: Stale reorder is 409
- **WHEN** the flag is true and the owner PATCHes reorder with `If-Match` not equal to the stored version
- **THEN** the response is 409 `trip_version_conflict` and a following GET shows the pre-edit trip

#### Scenario: Flag off reorder ignores If-Match
- **WHEN** the flag is false and the owner PATCHes a valid reorder with a wrong `If-Match`
- **THEN** the response is 200 and the order matches the body
