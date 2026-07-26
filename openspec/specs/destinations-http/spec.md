## Purpose

Public destinations HTTP layer — `GET /api/v1/destinations/search` and `GET /api/v1/destinations/{id}/readiness`. Router → `DestinationService` only; no geocode or DB access in the router. Readiness scoring is formula-backed via `compute_readiness` (P2: `search_available=False`).

## Requirements

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

The system SHALL register the destinations APIRouter (`prefix=/api/v1/destinations`) in `src/main.py`. The system SHALL expose `GET /api/v1/destinations/{destination_id}/readiness` that calls `DestinationService.get_readiness` only and returns `ApiResponse[DestinationReadinessOut]`. For an existing destination, readiness MUST use the P2 `compute_readiness` formula via the service (with `search_available=False` in P2) — not an interim stub. Unknown destination ids MUST raise `DestinationNotFoundError` (404). The endpoint MUST return 200 for existing destinations even when enrichment/index counts are zero (no Qdrant dependency in P2).

#### Scenario: Router is mounted on the app

- **WHEN** the FastAPI app starts
- **THEN** `/api/v1/destinations/search` is reachable (not 404 from missing route)

#### Scenario: Seeded Darjeeling readiness is limited

- **WHEN** Darjeeling (or equivalent seeded destination with `place_count >= 50`, unenriched) is requested via `/api/v1/destinations/{id}/readiness`
- **THEN** the response is 200 with `tier` `"limited"`, `score >= 0.35` and `< 0.7`, `enriched_pct` `0.0`, and `indexed_pct` `0.0`

#### Scenario: Unknown destination readiness is 404

- **WHEN** a client requests readiness for a random UUID that does not exist
- **THEN** the response is 404 with code `not_found`
