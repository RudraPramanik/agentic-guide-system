## Why

Steps 1.6–1.7 shipped JWT + Google OAuth auth with only a one-off validation script and a stub `tests/conftest.py`. We need a real pytest harness and unit/API coverage now so regressions are caught before middleware (1.8+) and P2. This also answers what “login/signup” means after 1.7: **Google OAuth login yes; email/password signup no.**

## What Changes

- Pull forward **step 1.11** harness pieces: `pytest.ini`, real `tests/conftest.py` (async client, test DB, auth fixtures), pytest deps
- Add **unit tests** for JWT, permissions (Bearer + cookie), auth schemas/exceptions, `UserRepository`, `AuthService` (mocked Google HTTP)
- Add **API/feature tests** for `/auth/me` (guest + cookie auth), `/auth/logout`, `/auth/google` (not configured), health
- Create `wandr_test` DB setup note / task
- **Defer** step 1.11 middleware assertions (`X-Request-ID`, rate-limit headers) until after 1.8 / 1.10
- **Non-goals:** email/password signup, refresh tokens, live Google OAuth e2e, steps 1.8–1.10 middleware implementation, P1 smoke script (1.12)

## Capabilities

### New Capabilities

- `pytest-harness`: Session test engine against `wandr_test`, per-test rollback sessions, ASGI `AsyncClient`, JWT auth fixtures
- `auth-test-coverage`: Unit + API tests for JWT/permissions/auth domain shipped in 1.6–1.7

### Modified Capabilities

- (none — product auth behavior unchanged; this change adds verification only)

## Impact

- **Code:** `pytest.ini`, `tests/conftest.py`, `tests/core/test_jwt.py`, `tests/core/test_permissions.py`, `tests/auth/test_*.py`; keep existing `tests/core/test_exceptions.py`
- **Deps:** `pytest==9.1.0`, `pytest-asyncio==1.4.0`, `pytest-mock==3.15.1`
- **Infra:** Postgres DB `wandr_test` (PostGIS) via docker
- **Docs:** `docs/context.md` notes harness ready; Next step stays **1.8** (middleware) unless this change is treated as completing 1.11 early — mark 1.11 partial/done for harness+auth tests, middleware tests still pending
- **Cites:** `docs/steps/step1.md` §1.11 (expanded beyond minimal router smoke)
