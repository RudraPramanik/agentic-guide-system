## ADDED Requirements

### Requirement: Redis RateLimiterBackend when REDIS_URL is set
When `get_settings().REDIS_URL` is a non-empty URL, `get_rate_limiter()` MUST return a Redis-backed implementation of `RateLimiterBackend` that preserves the same `is_allowed(key, limit, window) → (allowed, remaining)` contract as `InMemoryRateLimiter`. When `REDIS_URL` is empty, the system MUST continue using `InMemoryRateLimiter`.

Redis client usage MUST live only in the rate-limit backend module (or a dedicated `src/core/cache/` / redis helper module). Middleware MUST depend only on the Protocol. Redis timeouts MUST be explicit; Redis errors MUST fail open (request proceeds + warning logged) — same as the existing in-memory error boundary.

#### Scenario: Empty REDIS_URL keeps in-memory limiter
- **WHEN** `REDIS_URL` is empty or unset
- **THEN** `get_rate_limiter()` returns an in-memory backend and planner path limits still apply

#### Scenario: REDIS_URL selects Redis backend
- **WHEN** `REDIS_URL` is configured to a reachable Redis
- **THEN** `get_rate_limiter()` returns a Redis-backed `RateLimiterBackend` and exceeding the planner path limit still returns HTTP 429 with `Retry-After`

#### Scenario: Redis limiter error fails open
- **WHEN** the Redis rate-limiter backend raises during `is_allowed`
- **THEN** the request proceeds and a warning is logged (not blocked with 500)

## MODIFIED Requirements

### Requirement: RateLimiterBackend protocol
The backend SHALL implement a `RateLimiterBackend` protocol with `InMemoryRateLimiter` for empty `REDIS_URL` and a Redis-backed implementation when `REDIS_URL` is set. The middleware and route limit table behavior (settings-driven paths, exact match, 429 + `Retry-After`, fail-open) MUST remain unchanged aside from backend selection.

#### Scenario: In-memory backend for dev
- **WHEN** no Redis URL is configured
- **THEN** `InMemoryRateLimiter` handles sliding-window checks in-process

#### Scenario: Redis backend for prod URL
- **WHEN** `REDIS_URL` is set
- **THEN** a Redis `RateLimiterBackend` handles sliding-window checks via the same Protocol used by middleware
