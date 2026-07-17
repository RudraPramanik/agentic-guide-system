## Why

P1 auth is the next gate after BaseRepository: JWT dependencies and the Google OAuth domain must land before middleware and protected trip APIs. Steps 1.6 and 1.7a–c in `docs/steps/step1.md` define that work, but 1.6 is still stub-only on disk, there is no 1.7d, and the written prompts have a few architecture gaps we must correct before implementing.

## What Changes

- Implement **step 1.6** — `src/core/security/jwt.py` + `permissions.py` (`python-jose`), replacing stubs
- Implement **step 1.7a** — `src/auth/schemas.py` + `exceptions.py` (`email-validator`)
- Implement **step 1.7b** — `UserRepository` + `AuthService` (`httpx` + tenacity)
- Implement **step 1.7c** — auth router (4 endpoints) + register in `main.py` + Google OAuth settings in `config.py`
- **Procedure correction:** treat 1.6 as in-scope (not done); drop fictional 1.7d; keep a→b→c layering split
- **Design corrections** (see `design.md`): cookie+Bearer token resolution, single `AuthService` per request, config-driven token TTL / Google URLs, httpOnly session cookie aligned with blueprint

## Capabilities

### New Capabilities

- `jwt-permissions`: HS256 access tokens, `TokenPayload`, `require_auth` / `optional_auth` / `get_current_user_id` FastAPI dependencies (token from Bearer header or `wandr_token` cookie)
- `auth-domain`: Auth schemas/exceptions, `UserRepository`, `AuthService` (Google OAuth exchange + userinfo + upsert), router endpoints `/google`, `/callback`, `/me`, `/logout`

### Modified Capabilities

- (none — no main specs yet for auth)

## Impact

- **Code:** `src/core/security/*`, `src/auth/{schemas,exceptions,repository,service,router}.py`, `src/config.py`, `src/main.py`
- **Deps:** `python-jose[cryptography]==3.5.0`, `email-validator==2.3.0`, `httpx==0.28.1` (append to `requirements.txt` with why-comments)
- **APIs:** first domain router — `GET /api/v1/auth/google|callback|me`, `POST /api/v1/auth/logout`
- **AGENT.md:** Router→Service→Repository; httpx timeouts + tenacity; `WandrError` only; `get_settings()`; `ApiResponse[T]`
- **Docs:** update `docs/context.md` after validation (Next step → 1.8)
- **Non-goals:** request-logging middleware (1.8), rate limit (1.10), pytest harness (1.11), TripEditEvent (1.9), password auth, refresh tokens
