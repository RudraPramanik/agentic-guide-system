## MODIFIED Requirements

### Requirement: Destinations router registration and readiness stub

The system SHALL register the destinations APIRouter (`prefix=/api/v1/destinations`) in `src/main.py`. The system SHALL expose `GET /api/v1/destinations/{destination_id}/readiness` that calls `DestinationService.get_readiness` only and returns `ApiResponse[DestinationReadinessOut]`. For an existing destination, readiness MUST use the P2 `compute_readiness` formula via the service (with `search_available=False` in P2) — not an interim stub. Unknown destination ids MUST raise `DestinationNotFoundError` (404). The endpoint MUST return 200 for existing destinations even when enrichment/index counts are zero (no Qdrant dependency in P2). Unenriched limited-band HTTP acceptance MUST use a formula-true place-count floor (`place_count >= 100` preferred); `place_count >= 50` alone is only a seed/Overpass volume floor and MUST NOT be treated as sufficient for `tier=limited` / `score >= 0.35`.

#### Scenario: Router is mounted on the app

- **WHEN** the FastAPI app starts
- **THEN** `/api/v1/destinations/search` is reachable (not 404 from missing route)

#### Scenario: Seeded Darjeeling readiness is limited

- **WHEN** Darjeeling (or equivalent seeded destination with `place_count >= 100`, unenriched) is requested via `/api/v1/destinations/{id}/readiness`
- **THEN** the response is 200 with `tier` `"limited"`, `score >= 0.35` and `< 0.7`, `enriched_pct` `0.0`, and `indexed_pct` `0.0`

#### Scenario: Unknown destination readiness is 404

- **WHEN** a client requests readiness for a random UUID that does not exist
- **THEN** the response is 404 with code `not_found`
