## Purpose

In-memory rate limiting middleware for dev and single-worker deployments. Config-driven limits with fail-open error boundary; Redis backend deferred to P6.

## Requirements

### Requirement: Rate limit middleware on all routes

The system SHALL provide rate limit middleware with default limits read from `Settings` via `get_settings()`. Per-route overrides SHALL apply tighter limits on expensive paths (e.g. `/api/v1/planner/generate` at 10 req/min).

#### Scenario: Settings drive default limit

- **WHEN** `RATE_LIMIT_DEFAULT_REQUESTS=60` in settings
- **THEN** health endpoint responses include `X-RateLimit-Limit: 60`

#### Scenario: Planner route has tighter limit

- **WHEN** a request targets `/api/v1/planner/generate`
- **THEN** the configured planner limit (default 10 per 60 seconds) applies

### Requirement: RateLimiterBackend protocol

The backend SHALL implement a `RateLimiterBackend` protocol with `InMemoryRateLimiter` for dev and a documented extension point for Redis when `REDIS_URL` is set at P6.

#### Scenario: In-memory backend for dev

- **WHEN** no Redis URL is configured
- **THEN** `InMemoryRateLimiter` handles sliding-window checks in-process

### Requirement: Fail open on limiter errors

- **WHEN** the rate limiter backend raises an exception
- **THEN** the request proceeds with HTTP 200 and a warning is logged

### Requirement: Over limit returns 429

- **WHEN** a client exceeds the configured limit for a route
- **THEN** response status is 429 with `Retry-After` header and `ErrorResponse` body
