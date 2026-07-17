## Context

Auth (1.6–1.7) is implemented: Google OAuth start/callback, JWT cookies, guest `/me`. Product question after 1.7: users can **log in via Google** once `GOOGLE_CLIENT_*` are set; there is **no email/password signup** — `User` rows are created only via OAuth upsert. Guests work without login via `wandr_session`.

`tests/conftest.py` is still a stub; only `tests/core/test_exceptions.py` exists. Step 1.11 in `docs/steps/step1.md` defines the harness but also asserts middleware headers that do not exist until 1.8/1.10.

## Goals / Non-Goals

**Goals:**
- Runnable `pytest tests/ -v` with async support
- Unit coverage for JWT, permissions, auth schemas/exceptions, repository, service (mocked HTTP)
- API coverage for health + auth routes that exist today
- Document what login/signup means post-1.7 (Google only)

**Non-Goals:**
- Email/password registration or password reset
- Live Google OAuth integration tests (network + secrets)
- Middleware / rate-limit header tests (after 1.8 / 1.10)
- Implementing 1.8–1.10 or 1.12 smoke script in this change

## Decisions

### D1 — Pull pytest harness forward before middleware
- **Why:** Auth has enough surface to test now; waiting until after 1.10 leaves 1.6–1.7 unguarded.
- **Alt:** Strict step order 1.8→1.11 — rejected for this request; keep Next step as 1.8 for product code.

### D2 — Split unit vs API tests
- **Unit:** pure functions / deps with `Request` mocks; service with `httpx` mocked; repository against `db_session`
- **API:** `AsyncClient` + `get_db` override
- Cookie auth API test: set `wandr_token` cookie on client after creating a real User in DB (token `sub` must match DB user for `/me`)

### D3 — Skip middleware assertions from step 1.11 for now
- Do **not** add failing `test_x_request_id_present` / `test_rate_limit_headers_present`
- Track as follow-up tasks after 1.8 / 1.10 (or mark `@pytest.mark.skip` with reason — prefer omit until modules exist)

### D4 — Test DB `wandr_test` with metadata create_all
- Same approach as step 1.11: append `_test` to DB name, `CREATE EXTENSION postgis`, `Base.metadata.create_all`
- Require one-time `CREATE DATABASE wandr_test`
- Rollback per test for isolation

### D5 — AuthService Google calls: mock at httpx boundary
- Use `respx` only if already planned — **prefer** `unittest.mock.patch` / pytest-mock on `httpx.AsyncClient` to avoid new package unless needed
- Cover 401 → UnauthorizedError, timeout retry exhaustion → GoogleOAuthError

### D6 — Login/signup product stance (document only)
- Login path: `GET /auth/google` → Google → `GET /auth/callback` → JWT + cookie
- Signup = first-time upsert in `upsert_google_user` (no separate signup endpoint)
- Guests: `/auth/me` without token

## Risks / Trade-offs

- [test DB missing] → Task creates DB via docker exec; fail clearly if absent
- [create_app lifespan needs real DB/Qdrant] → ASGITransport may still run lifespan; if startup fails, override or use app without lifespan — verify during apply; mitigate with healthy docker compose + valid `.env`
- [AuthService.commit in upsert vs test rollback] → Use nested transaction / begin_nested or commit then cleanup; design apply to use `session.begin_nested()` savepoint if outer rollback insufficient after commit
- [Cookie `/me` needs matching User row] → Fixture `seeded_user` + token for that id

## Migration Plan

1. Install pytest deps + `pytest.ini`
2. Create `wandr_test` database
3. Replace conftest stub
4. Add unit then API test modules
5. `pytest tests/ -v` green
6. Update `docs/context.md` (1.11 harness + auth tests; Next step still **1.8**)

## Open Questions

- None blocking. If `create_app()` lifespan blocks ASGI tests, apply phase will use a test factory that skips ping or documents required docker health.
