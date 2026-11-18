## MODIFIED Requirements

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
