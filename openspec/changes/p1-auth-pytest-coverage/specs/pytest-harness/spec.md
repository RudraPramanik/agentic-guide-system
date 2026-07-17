## ADDED Requirements

### Requirement: Pytest configuration
The project SHALL provide a root `pytest.ini` with `asyncio_mode = auto`, `testpaths = tests`, and standard `test_*.py` discovery so `pytest tests/ -v` runs without extra flags.

#### Scenario: Discovery
- **WHEN** a developer runs `pytest tests/ -v`
- **THEN** pytest discovers tests under `tests/` and runs async tests without per-file asyncio markers

### Requirement: Test database fixtures
The harness SHALL provide a session-scoped async engine against a `wandr_test` database (derived from `DATABASE_URL`), ensure PostGIS, create metadata tables once, and dispose after the session. Function-scoped `db_session` MUST roll back after each test.

#### Scenario: Isolated writes
- **WHEN** a test inserts a row via `db_session` and the test ends
- **THEN** a subsequent test does not see that row (rollback isolation)

### Requirement: ASGI HTTP client fixture
The harness SHALL provide an `AsyncClient` bound to `create_app()` with `get_db` overridden to the test session, and SHALL clear dependency overrides after the test.

#### Scenario: Client hits health
- **WHEN** the client GETs `/api/v1/health` against a healthy test DB
- **THEN** the response is 200 with `success=true` and `data.status=ok`

### Requirement: Auth token fixtures
The harness SHALL provide `auth_token` and `auth_headers` fixtures that mint a valid JWT via `create_access_token` for a synthetic user id/email.

#### Scenario: Headers usable
- **WHEN** `auth_headers` is applied to a request
- **THEN** the Authorization Bearer value verifies via `verify_token`
