## ADDED Requirements

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
