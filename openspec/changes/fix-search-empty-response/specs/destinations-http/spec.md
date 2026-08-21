## ADDED Requirements

### Requirement: Destination search always returns HTTP before the client abort window
`GET /api/v1/destinations/search` MUST complete with an HTTP status and JSON envelope. A Nominatim cache-aside miss MUST be bounded by `SEARCH_GEOCODE_TIMEOUT_SECONDS` from `get_settings()` (default 8 seconds). If geocode exceeds that budget, the search MUST behave as an un-geocodable query (`404` `not_found` via `DestinationNotFoundError`) and MUST NOT leave the TCP connection open until the client aborts. DB ILIKE hits MUST still return `200` without calling Nominatim. The router MUST NOT import geocode.

#### Scenario: Cache miss that exceeds the geocode budget returns 404
- **WHEN** a search query misses the destination table and geocode does not finish within `SEARCH_GEOCODE_TIMEOUT_SECONDS`
- **THEN** the response is HTTP 404 with `ErrorResponse` code `not_found` (not a dropped connection / empty body)

#### Scenario: Cached name still returns 200
- **WHEN** a client requests `/api/v1/destinations/search?q=Darjeeling` and the row exists
- **THEN** the response is 200 with a non-empty `data` array (Nominatim is not required for this hit)
