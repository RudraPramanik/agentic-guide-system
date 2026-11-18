## Purpose

Public destinations HTTP layer — `GET /api/v1/destinations/search`, `GET /api/v1/destinations/resolve`, `GET /api/v1/destinations/{id}/readiness`, and `POST /api/v1/destinations/{id}/prepare`. Router → `DestinationService` only; no geocode or DB access in the router. Readiness scoring is formula-backed via `compute_readiness` (P2: `search_available=False`).

## Requirements

### Requirement: Public destinations resolve HTTP endpoint

The system SHALL expose additive `GET /api/v1/destinations/resolve` (no auth) with query param `q` (min_length=2, max_length=200) that returns `ApiResponse[DestinationResolveOut]` with discriminated `kind` of `destination`, `hubs`, or `ambiguous`. Oversized country/region queries MUST return `kind=hubs` (HITL) and MUST NOT treat the country centroid alone as the plannable destination. City-scale queries MUST return `kind=destination`. Multiple city-scale matches MUST return `kind=ambiguous`. Existing `GET /search` and prepare/generate contracts MUST remain unchanged. Resolve MUST share the same rate-limit class as search (default 20/min/IP on the resolve path).

#### Scenario: City resolve returns destination

- **WHEN** a client requests `/api/v1/destinations/resolve?q=Darjeeling` for a city-scale place
- **THEN** the response is 200 with `kind` `"destination"` and a populated `destination` object

#### Scenario: Country resolve returns hubs

- **WHEN** a client requests `/api/v1/destinations/resolve?q=Japan` (or equivalent oversized admin)
- **THEN** the response is 200 with `kind` `"hubs"` and a non-empty `hubs` list of city-scale destinations

### Requirement: Public destinations search HTTP endpoint

The system SHALL expose `GET /api/v1/destinations/search` (no auth) that accepts query param `q` (min_length=2, max_length=200), calls `DestinationService.search` only, and returns `ApiResponse[list[DestinationOut]]`. The router MUST NOT import geocode or touch the repository/DB directly. Unknown/un-geocodable queries MUST surface as 404 `ErrorResponse` with code `not_found` (via `DestinationNotFoundError`).

#### Scenario: Search Darjeeling returns destination JSON

- **WHEN** the server is running and a client requests `/api/v1/destinations/search?q=Darjeeling`
- **THEN** the response is 200 with `success` true (or equivalent envelope), a non-empty `data` array, and each item includes populated `lat`/`lng` (and destination identity fields)

#### Scenario: Nonsense query returns 404

- **WHEN** a client requests `/api/v1/destinations/search?q=XyzzyNonexistent999`
- **THEN** the response is 404 with code `not_found`

#### Scenario: Browser and Swagger can exercise search

- **WHEN** an operator opens `http://localhost:8000/docs` and/or navigates to the search URL in a browser after uvicorn is up
- **THEN** they can see the search operation documented and obtain the same Darjeeling JSON result without writing application code

### Requirement: Destinations router registration and readiness stub

The system SHALL register the destinations APIRouter (`prefix=/api/v1/destinations`) in `src/main.py`. The system SHALL expose `GET /api/v1/destinations/{destination_id}/readiness` that calls `DestinationService.get_readiness` only and returns `ApiResponse[DestinationReadinessOut]`. The response data MUST keep the fields `destination_id`, `score`, `tier`, `place_count`, `enriched_pct`, `indexed_pct`, and `message`. The route MUST NOT add or remove those fields. Optional query `days` MUST be an integer from 1 to 30 and MUST default to 1 when omitted. A missing or out-of-range `days` value MUST return 422 and MUST NOT score. The router MUST NOT touch the database.

When `READINESS_V2_ENABLED` is false, readiness MUST use the P2 `compute_readiness` formula via the service. Unknown destination ids MUST raise `DestinationNotFoundError` (404). The endpoint MUST return 200 for existing destinations even when enrichment and index counts are zero. Unenriched limited-band HTTP acceptance MUST use a formula-true place-count floor (`place_count >= 100` preferred); `place_count >= 50` alone is only a seed volume floor and MUST NOT be treated as sufficient for `tier=limited` or `score >= 0.35`. With the flag false, the body for a given destination MUST be identical whether `days` is omitted or set.

When `READINESS_V2_ENABLED` is true, the same route MUST return the V2 tier for that `days` value, with `place_count` equal to the usable-place count, and MUST still return 200 for an existing destination whose tier is `limited` or `sparse`. The route MUST NOT return 409 because readiness is low. The absolute place-count floor on generate stays on its own route.

#### Scenario: Router is mounted on the app

- **WHEN** the FastAPI app starts
- **THEN** `/api/v1/destinations/search` is reachable (not 404 from missing route)

#### Scenario: Seeded Darjeeling readiness is limited

- **WHEN** Darjeeling (or an equivalent seeded destination with `place_count >= 100`, unenriched) is requested via `/api/v1/destinations/{id}/readiness` and `READINESS_V2_ENABLED` is false
- **THEN** the response is 200 with `tier` `"limited"`, `score >= 0.35` and `< 0.7`, `enriched_pct` `0.0`, and `indexed_pct` `0.0`

#### Scenario: Unknown destination readiness is 404

- **WHEN** a client requests readiness for a random UUID that does not exist
- **THEN** the response is 404 with code `not_found`

#### Scenario: Days query does not change the flag-off body

- **WHEN** the flag is false and the same destination is requested with `days` omitted and with `days=3`
- **THEN** both 200 bodies have the same score, tier, place count, percentages, and message

#### Scenario: Flag-on three-day request can be limited without a new field

- **WHEN** the flag is true and the client requests `days=3` for a destination whose usable places are ten places in one cluster
- **THEN** the response is 200, `tier` is `limited`, and the data object has only the existing readiness fields

#### Scenario: Days out of range is 422

- **WHEN** the client requests readiness with `days=0`
- **THEN** the response is 422 and no readiness tier is returned

### Requirement: Public destination prepare HTTP endpoint

The system SHALL expose `POST /api/v1/destinations/{destination_id}/prepare` with no auth. The router MUST call `DestinationService` only (no geocode, Overpass, or repository in the router) and MUST return `ApiResponse` wrapping a prepare result DTO that includes `destination_id`, `status` (`ready` or `preparing`), and `place_count`. Optional JSON body MAY include `radius_km` (default 30, maximum 50). HTTP 200 MUST mean already at or above the planner place floor (`status=ready`). HTTP 202 MUST mean a scrape is in flight or was started (`status=preparing`). Unknown ids MUST remain 404 `not_found`. Search and readiness routes MUST keep their existing contracts (search MUST NOT scrape Overpass).

#### Scenario: Prepare is documented and mounted

- **WHEN** the FastAPI app starts
- **THEN** `POST /api/v1/destinations/{destination_id}/prepare` is reachable (not 404 from a missing route) and appears in OpenAPI `/docs`

#### Scenario: Search still does not scrape

- **WHEN** a client calls `GET /api/v1/destinations/search?q=` for a new place
- **THEN** the response remains a geocoded destination list (possibly `place_count=0`) without waiting on Overpass

#### Scenario: Prepare envelope is ApiResponse

- **WHEN** prepare succeeds with 200 or 202
- **THEN** the body is `ApiResponse` with `success` true and prepare fields in `data` (not SSE, not a bare dict)

### Requirement: Destination search always returns HTTP before the client abort window
`GET /api/v1/destinations/search` MUST complete with an HTTP status and JSON envelope. A Nominatim cache-aside miss MUST be bounded by `SEARCH_GEOCODE_TIMEOUT_SECONDS` from `get_settings()` (default 8 seconds). If geocode exceeds that budget, the search MUST behave as an un-geocodable query (`404` `not_found` via `DestinationNotFoundError`) and MUST NOT leave the TCP connection open until the client aborts. DB ILIKE hits MUST still return `200` without calling Nominatim. The router MUST NOT import geocode.

#### Scenario: Cache miss that exceeds the geocode budget returns 404
- **WHEN** a search query misses the destination table and geocode does not finish within `SEARCH_GEOCODE_TIMEOUT_SECONDS`
- **THEN** the response is HTTP 404 with `ErrorResponse` code `not_found` (not a dropped connection / empty body)

#### Scenario: Cached name still returns 200
- **WHEN** a client requests `/api/v1/destinations/search?q=Darjeeling` and the row exists
- **THEN** the response is 200 with a non-empty `data` array (Nominatim is not required for this hit)
