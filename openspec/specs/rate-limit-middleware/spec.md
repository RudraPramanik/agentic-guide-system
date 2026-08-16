## Purpose

Rate limiting middleware with config-driven limits and fail-open error boundary. In-memory backend for empty `REDIS_URL`; Redis-backed `RateLimiterBackend` when `REDIS_URL` is set (P6).

## Requirements

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

### Requirement: RateLimiterBackend protocol

The backend SHALL implement a `RateLimiterBackend` protocol with `InMemoryRateLimiter` for empty `REDIS_URL` and a Redis-backed implementation when `REDIS_URL` is set. The middleware and route limit table behavior (settings-driven paths, exact match, 429 + `Retry-After`, fail-open) MUST remain unchanged aside from backend selection.

#### Scenario: In-memory backend for dev

- **WHEN** no Redis URL is configured
- **THEN** `InMemoryRateLimiter` handles sliding-window checks in-process

#### Scenario: Redis backend for prod URL

- **WHEN** `REDIS_URL` is set
- **THEN** a Redis `RateLimiterBackend` handles sliding-window checks via the same Protocol used by middleware

### Requirement: Redis RateLimiterBackend when REDIS_URL is set

When `get_settings().REDIS_URL` is a non-empty URL, `get_rate_limiter()` MUST return a Redis-backed implementation of `RateLimiterBackend` that preserves the same `is_allowed(key, limit, window) → (allowed, remaining)` contract as `InMemoryRateLimiter` (sliding-window semantics preferred). When `REDIS_URL` is empty, the system MUST continue using `InMemoryRateLimiter`.

Redis client usage MUST live only in the rate-limit backend module (or a dedicated `src/core/cache/` / redis helper module). Middleware MUST depend only on the Protocol. Redis timeouts MUST be explicit; Redis errors MUST fail open (request proceeds + warning logged) — same as the existing in-memory error boundary. Step **6.4** delivers this selection (no longer deferred as unimplemented).

#### Scenario: Empty REDIS_URL keeps in-memory limiter

- **WHEN** `REDIS_URL` is empty or unset
- **THEN** `get_rate_limiter()` returns an in-memory backend and planner path limits still apply

#### Scenario: REDIS_URL selects Redis backend

- **WHEN** `REDIS_URL` is configured to a reachable Redis
- **THEN** `get_rate_limiter()` returns a Redis-backed `RateLimiterBackend` and exceeding the planner path limit still returns HTTP 429 with `Retry-After`

#### Scenario: Redis limiter error fails open

- **WHEN** the Redis rate-limiter backend raises during `is_allowed`
- **THEN** the request proceeds and a warning is logged (not blocked with 500)

### Requirement: Fail open on limiter errors

The system SHALL fail open when the rate limiter backend raises an exception: the request MUST proceed (not blocked) and a warning MUST be logged.

#### Scenario: Limiter exception does not block the request

- **WHEN** the rate limiter backend raises an exception
- **THEN** the request proceeds with HTTP 200 and a warning is logged

### Requirement: Over limit returns 429

The system SHALL return HTTP 429 when a client exceeds the configured limit for a route. The response MUST include a `Retry-After` header and an `ErrorResponse` body.

#### Scenario: Exceeding the route limit returns 429

- **WHEN** a client exceeds the configured limit for a route
- **THEN** response status is 429 with `Retry-After` header and `ErrorResponse` body

### Requirement: User-keyed trip-edit rate limit dependency

The system SHALL provide Settings fields `RATE_LIMIT_TRIP_EDIT_REQUESTS` (default 20) and `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` (default 60) via `get_settings()`. The system SHALL expose a FastAPI dependency `rate_limit_trip_edit` that Depends on `require_auth`, calls `get_rate_limiter().is_allowed` with key `"{user_id}:trip_edit"` and the trip-edit settings limits, and returns the `TokenPayload` when allowed. When not allowed, it MUST raise a `WandrError` (preferably `RateLimitedError`) with `status_code=429` and `code="rate_limit_exceeded"`. When the limiter backend raises, the dependency MUST fail open (return payload; do not block the request). Trip-edit UUID paths MUST NOT be added to `_route_limit_table`; middleware IP/path default MAY still apply (dual limit is acceptable). Router handlers for the four edit endpoints MUST Depends on `rate_limit_trip_edit` (not bare `require_auth` alone).

#### Scenario: Settings expose trip-edit limits

- **WHEN** `get_settings()` is loaded after step 7.3
- **THEN** `RATE_LIMIT_TRIP_EDIT_REQUESTS` defaults to 20 and `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` defaults to 60

#### Scenario: Exceeding user-keyed edit limit returns 429

- **WHEN** the same authenticated user exceeds the trip-edit request limit within the window (e.g. 21st call with a mock limiter)
- **THEN** the edit endpoint returns HTTP 429 with `code="rate_limit_exceeded"` and the trip is unchanged

#### Scenario: Limiter exception fails open on edit dependency

- **WHEN** `get_rate_limiter().is_allowed` raises during `rate_limit_trip_edit`
- **THEN** the dependency allows the request to proceed (does not raise 429/500 from the limiter failure alone)

#### Scenario: Edit paths absent from route limit table

- **WHEN** `_route_limit_table()` is inspected after step 7.3
- **THEN** it does not contain UUID-templated trip edit path entries

### Requirement: IP-keyed destination-prepare rate limit dependency

The system SHALL provide Settings fields `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` (default 5) and `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` (default 60) via `get_settings()`. The prepare HTTP handler MUST apply an IP-keyed limiter dependency (key pattern `{ip}:dest_prepare`) using `get_rate_limiter().is_allowed`. When not allowed, it MUST raise `RateLimitedError` (HTTP 429, code `rate_limit_exceeded`). When the limiter backend raises, the dependency MUST fail open. The UUID prepare path MUST NOT be added to `_route_limit_table` (exact path match cannot key UUID routes). Existing planner (10/min) and destinations-search (20/min) table rows MUST remain unchanged.

#### Scenario: Settings expose prepare limits

- **WHEN** `get_settings()` is loaded after this change
- **THEN** `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` defaults to 5 and `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` defaults to 60

#### Scenario: Exceeding prepare limit returns 429

- **WHEN** the same client IP exceeds the prepare request limit within the window
- **THEN** a subsequent prepare returns HTTP 429 with `code="rate_limit_exceeded"` and no new scrape is started

#### Scenario: Limiter exception fails open on prepare

- **WHEN** `get_rate_limiter().is_allowed` raises during the prepare limiter
- **THEN** the request proceeds (does not fail 429/500 from the limiter failure alone)

#### Scenario: Prepare UUID path absent from route limit table

- **WHEN** `_route_limit_table()` is inspected after this change
- **THEN** it does not contain a UUID-templated destinations prepare path
