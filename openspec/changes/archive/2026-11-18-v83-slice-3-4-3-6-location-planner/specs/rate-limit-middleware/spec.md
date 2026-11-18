## MODIFIED Requirements

### Requirement: Settings-driven ordered route limit table

The system SHALL resolve per-path rate limits via an ordered table built from `get_settings()` (planner path, then destinations-search path, then the three location paths). Lookup MUST be exact path equality. When no row matches, the system SHALL use `RATE_LIMIT_DEFAULT_REQUESTS` / `RATE_LIMIT_DEFAULT_WINDOW_SECONDS`. Fail-open on limiter backend errors MUST remain unchanged. Existing planner limit behavior for the configured planner path MUST remain 10 requests per 60 seconds by default.

`RATE_LIMIT_LOCATIONS_SEARCH_PATH`, `RATE_LIMIT_LOCATIONS_RESOLVE_PATH`, and `RATE_LIMIT_LOCATIONS_SEARCH_AREA_PATH` MUST default to `/api/v1/locations/search`, `/api/v1/locations/resolve`, and `/api/v1/locations/search-area`. Each MUST use `RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS` and `RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS` (defaults 20 and 60). The system MUST NOT add a separate numeric budget for these paths. `.env.example` MUST document the three path names and those defaults.

#### Scenario: Destinations search path resolves to 20/60

- **WHEN** `_resolve_limits` is called with `RATE_LIMIT_DESTINATIONS_SEARCH_PATH`
- **THEN** it returns limit `20` and window `60` (defaults)

#### Scenario: Planner path limit unchanged

- **WHEN** `_resolve_limits` is called with `RATE_LIMIT_PLANNER_PATH`
- **THEN** it returns limit `10` and window `60` (defaults)

#### Scenario: Unrelated path uses global default

- **WHEN** `_resolve_limits` is called with `/api/v1/health`
- **THEN** it returns `RATE_LIMIT_DEFAULT_REQUESTS` and `RATE_LIMIT_DEFAULT_WINDOW_SECONDS`

#### Scenario: Live search responses advertise limit 20

- **WHEN** a client calls `GET /api/v1/destinations/search?q=Darjeeling` with the server running
- **THEN** the response includes `X-RateLimit-Limit: 20` (not 60)

#### Scenario: Over limit on destinations search returns 429

- **WHEN** a client issues more than 20 requests to `/api/v1/destinations/search` within the window from the same IP
- **THEN** a subsequent request returns HTTP 429 with `Retry-After`

#### Scenario: Location search uses the destinations-search budget

- **WHEN** a client calls `POST /api/v1/locations/search` and the same client calls `POST /api/v1/locations/resolve` or `POST /api/v1/locations/search-area`
- **THEN** each path is limited to 20 requests per 60 seconds per IP, and the 21st request on that path returns HTTP 429 with `Retry-After`
