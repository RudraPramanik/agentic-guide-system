## Purpose

Documented amendments and production hardening for P1 steps 1.9–1.12: config-driven rate limits, failure-path tests, TripEditEvent smoke coverage, and explicit no-bulk-upgrade policy during P1 finish.

## Requirements

### Requirement: Step amendments documented before P1 finish

The project SHALL maintain documented amendments to `docs/steps/step1.md` sections 1.9–1.12 covering config-driven rate limits, failure tests, TripEditEvent smoke coverage, and explicit no-bulk-upgrade policy.

#### Scenario: Implementer reads amendments

- **WHEN** an agent implements step 1.10
- **THEN** rate limit values are sourced from `get_settings()` not hardcoded module constants

### Requirement: No bulk package upgrade during P1 steps 1.9–1.12

Steps 1.9–1.12 SHALL NOT require upgrading existing pinned dependencies (FastAPI, SQLAlchemy, litellm, etc.). Only `shapely` may be added at step 1.12.

#### Scenario: requirements.txt diff for P1 finish

- **WHEN** steps 1.9–1.12 are complete
- **THEN** the only new production dependency line is `shapely` (pytest packages may already exist from partial 1.11)

### Requirement: Rate limit middleware stub on planner routes

The system SHALL provide rate limit middleware with limits read from `Settings` via `get_settings()`. The backend SHALL implement a `RateLimiterBackend` protocol with `InMemoryRateLimiter` for dev and a documented extension point for Redis at P6.

#### Scenario: Settings drive default limit

- **WHEN** `RATE_LIMIT_DEFAULT_REQUESTS=60` in settings
- **THEN** health endpoint responses include `X-RateLimit-Limit: 60`

#### Scenario: Middleware error fails open

- **WHEN** the rate limiter backend raises an exception
- **THEN** the request proceeds with HTTP 200 and a warning is logged

#### Scenario: Over limit returns 429

- **WHEN** a client exceeds the configured limit for a route
- **THEN** response status is 429 with `Retry-After` header and `ErrorResponse` body

### Requirement: Pytest harness supports async API tests

The test harness SHALL include tests asserting `X-Request-ID` and rate limit headers after step 1.10, plus a fail-open failure test using mocks.

#### Scenario: Fail-open test

- **WHEN** rate limiter backend is mocked to raise
- **THEN** health request returns 200 not 500

### Requirement: TripEditEvent table exists after migration 003

After migration 003, the P1 smoke script SHALL verify `TripEditEvent` insert and trip CASCADE delete behavior in a rolled-back transaction.

#### Scenario: Smoke test covers edit events

- **WHEN** `python scripts/test_p1_smoke.py` runs after step 1.12
- **THEN** output includes a passed TripEditEvent section
