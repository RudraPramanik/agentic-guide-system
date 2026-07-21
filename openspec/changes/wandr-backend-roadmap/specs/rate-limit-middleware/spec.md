## ADDED Requirements

### Requirement: Rate limit middleware stub on planner routes

The system SHALL provide `RequestRateLimitMiddleware` in `src/core/middleware/rate_limit.py` limiting `/api/v1/planner/generate` to 10 requests per minute per IP.

#### Scenario: Under limit passes

- **WHEN** a client sends fewer than 11 requests per minute to planner generate
- **THEN** requests proceed normally

#### Scenario: Over limit returns 429

- **WHEN** an IP exceeds 10 requests per minute on planner generate
- **THEN** response status is 429 with `Retry-After` header

#### Scenario: Middleware error fails open

- **WHEN** the rate limiter internal store raises an error
- **THEN** the request proceeds and a warning is logged

### Requirement: Dev uses in-memory store

The system SHALL use an in-memory counter when `REDIS_URL` is empty.

#### Scenario: No Redis configured

- **WHEN** `REDIS_URL` is unset in development
- **THEN** rate limiting still functions using process memory
