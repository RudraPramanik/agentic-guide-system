## ADDED Requirements

### Requirement: Middleware header assertions after rate limit

The test harness SHALL assert `X-Request-ID` response header on health and auth endpoints once rate limit middleware is registered.

#### Scenario: Health returns request id

- **WHEN** test client calls GET /api/v1/health
- **THEN** response includes X-Request-ID header

## MODIFIED Requirements

### Requirement: Pytest harness supports async API tests

The system SHALL provide `tests/conftest.py` with async test client, test database, and fixtures for auth tokens.

#### Scenario: Auth API tests run green

- **WHEN** `pytest tests/auth/ -v` runs with test database configured
- **THEN** all auth tests pass including middleware header checks when step 1.10 is complete
