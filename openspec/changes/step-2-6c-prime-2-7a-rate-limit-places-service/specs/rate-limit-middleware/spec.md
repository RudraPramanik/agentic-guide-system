## ADDED Requirements

### Requirement: Settings-driven ordered route limit table

The system SHALL resolve per-path rate limits via an ordered table built from `get_settings()` (planner path, then destinations-search path). Lookup MUST be exact path equality. When no row matches, the system SHALL use `RATE_LIMIT_DEFAULT_REQUESTS` / `RATE_LIMIT_DEFAULT_WINDOW_SECONDS`. Fail-open on limiter backend errors MUST remain unchanged. Existing planner limit behavior for the configured planner path MUST remain 10 requests per 60 seconds by default.

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

## MODIFIED Requirements

### Requirement: Rate limit middleware on all routes

The system SHALL provide rate limit middleware with default limits read from `Settings` via `get_settings()`. Per-route overrides SHALL apply tighter limits on expensive paths via an ordered settings-driven table with exact path match — including `/api/v1/planner/generate` at 10 req/min and `/api/v1/destinations/search` at 20 req/min (defaults). Paths not listed SHALL use the global default (60 req/min by default).

#### Scenario: Settings drive default limit

- **WHEN** `RATE_LIMIT_DEFAULT_REQUESTS=60` in settings
- **THEN** health endpoint responses include `X-RateLimit-Limit: 60`

#### Scenario: Planner route has tighter limit

- **WHEN** a request targets `/api/v1/planner/generate`
- **THEN** the configured planner limit (default 10 per 60 seconds) applies

#### Scenario: Destinations search has Nominatim-protecting limit

- **WHEN** a request targets `/api/v1/destinations/search`
- **THEN** the configured destinations-search limit (default 20 per 60 seconds) applies
