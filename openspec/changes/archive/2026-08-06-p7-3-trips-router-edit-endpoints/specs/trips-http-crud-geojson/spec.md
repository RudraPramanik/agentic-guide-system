## MODIFIED Requirements

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
