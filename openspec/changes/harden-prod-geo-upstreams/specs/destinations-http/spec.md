## MODIFIED Requirements

### Requirement: Public destinations search HTTP endpoint

The system SHALL expose `GET /api/v1/destinations/search` (no auth) that accepts query param `q` (min_length=2, max_length=200), calls `DestinationService.search` only, and returns `ApiResponse[list[DestinationOut]]`. The router MUST NOT import geocode or touch the repository/DB directly. Unknown/un-geocodable queries (geocode returned `None`, including after the geocode time budget) MUST surface as 404 `ErrorResponse` with code `not_found` (via `DestinationNotFoundError`). When the geocode upstream rejects the client (policy/rate-limit), the endpoint MUST surface 502 `ErrorResponse` with code `external_service_error` and details identifying service `nominatim` (via `ExternalServiceError`) — MUST NOT return 404 `not_found` for that path.

#### Scenario: Search Darjeeling returns destination JSON

- **WHEN** the server is running and a client requests `/api/v1/destinations/search?q=Darjeeling`
- **THEN** the response is 200 with `success` true (or equivalent envelope), a non-empty `data` array, and each item includes populated `lat`/`lng` (and destination identity fields)

#### Scenario: Nonsense query returns 404

- **WHEN** a client requests `/api/v1/destinations/search?q=XyzzyNonexistent999`
- **THEN** the response is 404 with code `not_found`

#### Scenario: Nominatim policy block returns 502

- **WHEN** a client requests search for a plausible city name and Nominatim responds with HTTP 403 (or equivalent policy rejection)
- **THEN** the response is 502 with code `external_service_error` and details including service `nominatim`

#### Scenario: Browser and Swagger can exercise search

- **WHEN** an operator opens `http://localhost:8000/docs` and/or navigates to the search URL in a browser after uvicorn is up
- **THEN** they can see the search operation documented and obtain the same Darjeeling JSON result without writing application code

### Requirement: Destination search always returns HTTP before the client abort window
`GET /api/v1/destinations/search` MUST complete with an HTTP status and JSON envelope. A Nominatim cache-aside miss MUST be bounded by `SEARCH_GEOCODE_TIMEOUT_SECONDS` from `get_settings()` (default 8 seconds). If geocode exceeds that budget, the search MUST behave as an un-geocodable query (`404` `not_found` via `DestinationNotFoundError`) and MUST NOT leave the TCP connection open until the client aborts. If geocode raises `ExternalServiceError` within the budget, the search MUST return `502` `external_service_error` (not 404). DB ILIKE hits MUST still return `200` without calling Nominatim. The router MUST NOT import geocode.

#### Scenario: Cache miss that exceeds the geocode budget returns 404
- **WHEN** a search query misses the destination table and geocode does not finish within `SEARCH_GEOCODE_TIMEOUT_SECONDS`
- **THEN** the response is HTTP 404 with `ErrorResponse` code `not_found` (not a dropped connection / empty body)

#### Scenario: Upstream rejection within budget returns 502
- **WHEN** a search query misses the destination table and geocode raises `ExternalServiceError` before the time budget expires
- **THEN** the response is HTTP 502 with `ErrorResponse` code `external_service_error`

#### Scenario: Cached name still returns 200
- **WHEN** a client requests `/api/v1/destinations/search?q=Darjeeling` and the row exists
- **THEN** the response is 200 with a non-empty `data` array (Nominatim is not required for this hit)
