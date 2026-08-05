## MODIFIED Requirements

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
