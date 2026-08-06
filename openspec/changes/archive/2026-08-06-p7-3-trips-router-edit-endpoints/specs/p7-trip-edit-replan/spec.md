## MODIFIED Requirements

### Requirement: Day-scoped edit HTTP API

The system SHALL expose these authenticated endpoints under `/api/v1/trips` via `src/trips/router.py` (registered on the FastAPI app; visible in OpenAPI):

| Method | Path | Body |
|--------|------|------|
| PATCH | `/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` (`ReorderStopsIn`) |
| DELETE | `/{id}/days/{day}/stops/{place_id}` | — |
| POST | `/{id}/days/{day}/stops` | `{ "place_id": uuid }` (`AddStopIn`) |
| POST | `/{id}/days/{day}/reoptimize` | — |

Each successful response MUST be `ApiResponse[TripOut]`. All four MUST use `require_auth` (via `rate_limit_trip_edit` or equivalent chain) and ownership (`trip.user_id == caller`); guests MUST NOT edit via session alone (claim first). Ownership miss → 403; missing/soft-deleted trip → 404. Edit routes MUST apply a user-keyed rate-limit dependency (`rate_limit_trip_edit`) in addition to any global middleware default; exceeded limit → 429. Paths MUST NOT be added as broken exact-match UUID entries in `_route_limit_table`. Router MUST call `TripService` only (no repository/DB, no `travel_engine`, no planner/LLM imports). Domain errors MUST surface through the global `WandrError` handler (422/409/404/403 as raised by the service).

#### Scenario: OpenAPI lists four edit routes

- **WHEN** the FastAPI OpenAPI schema is inspected after step 7.3
- **THEN** it includes the four paths above under the trips tag

#### Scenario: Owner reorder returns TripOut

- **WHEN** the authenticated owner PATCHes reorder with a valid permutation of day stops
- **THEN** the response is 200 `ApiResponse[TripOut]` and stop `order_in_day`, times, and polylines reflect the requested order

#### Scenario: Guest cannot edit

- **WHEN** an unauthenticated or guest-only caller invokes any P7 edit endpoint
- **THEN** the response is 401 (or auth challenge) and the trip is unchanged

#### Scenario: Non-owner is forbidden

- **WHEN** an authenticated user who does not own the trip calls a P7 edit endpoint
- **THEN** the response is 403 and the trip is unchanged

#### Scenario: Edit rate limit exceeded

- **WHEN** the same authenticated user exceeds `RATE_LIMIT_TRIP_EDIT_REQUESTS` within the window
- **THEN** the response is 429 and the trip is unchanged

#### Scenario: Validation failure leaves trip unchanged

- **WHEN** an authenticated owner POSTs add that would drop other stops (or otherwise fails service validation)
- **THEN** the response is 422 and a subsequent GET matches the pre-edit trip
