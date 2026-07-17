## Context

P1 DB foundation is complete (`Base`, session, migrations 001–002, models, `BaseRepository`). Auth stubs under `src/core/security/` and `src/auth/` are still one-line placeholders. Blueprint §1.6–1.7 and `docs/steps/step1.md` steps 1.6 / 1.7a–c define JWT + Google OAuth. `docs/context.md` incorrectly lists Next step as 1.6 while claiming 1.6–1.12 pending — code confirms 1.6 is not done.

Procedure assessment: the **a→b→c split is correct** (schemas → repo/service → router) and is the right way to enforce Router→Service→Repository. There is **no 1.7d** in `step1.md`. Jumping straight to 1.7 without 1.6 is wrong because the router depends on `create_access_token` and `optional_auth`.

## Goals / Non-Goals

**Goals:**
- Working JWT create/verify + FastAPI auth dependencies
- Google OAuth login path with typed failures (401 vs 502)
- Guest `/auth/me` with durable `session_id` cookie for later trip claiming
- Clean layering, config-driven secrets/TTL/URLs, resilient httpx calls

**Non-Goals:**
- Middleware chain (1.8+), rate limiting (1.10), pytest harness (1.11)
- Password/email signup, refresh tokens, Google ID-token verification (userinfo access-token path only)
- Claiming anonymous trips on login (trip domain later)

## Decisions

### D1 — Implementation order: 1.6 → 1.7a → 1.7b → 1.7c
- **Why:** Matches dependency graph and the intentional layering split.
- **Alt:** Combine into one prompt — rejected (historically puts SQL in routers).

### D2 — Token resolution: Bearer header first, then `wandr_token` cookie
- **Problem in step prompt:** Callback sets httpOnly `wandr_token`, but `optional_auth` / `OAuth2PasswordBearer` only read `Authorization`. Post-login `/auth/me` would always look like a guest.
- **Decision:** Shared helper `_extract_token(request)` used by `require_auth` and `optional_auth`: prefer `Authorization: Bearer …`, else cookie `wandr_token`.
- **Alt:** Cookie-only or header-only — rejected; SPA may use either.

### D3 — Session cookie httpOnly=True (blueprint alignment)
- **Problem:** Step 1.7c sets `wandr_session` with `httponly=False`; blueprint says anonymous session UUID in httpOnly cookie.
- **Decision:** `wandr_session` is httpOnly, SameSite=lax, `secure` only when `ENVIRONMENT == "production"`. Frontend gets `session_id` from `/auth/me` JSON body — no JS cookie read required.
- **Alt:** Keep readable cookie for SPA — rejected; body already returns `session_id`.

### D4 — One `AuthService` instance per handler
- **Problem:** Step 1.7c constructs `AuthService(db)` three times in callback.
- **Decision:** `svc = AuthService(db)` once; reuse for exchange → userinfo → upsert.

### D5 — Config for TTL and Google endpoints (AGENT.md)
- **Problem:** Prompt hardcodes `ACCESS_TOKEN_EXPIRE_DAYS = 7` and Google URLs.
- **Decision:** Add settings (with defaults): `ACCESS_TOKEN_EXPIRE_DAYS: int = 7`, `GOOGLE_TOKEN_URL`, `GOOGLE_USERINFO_URL`, `GOOGLE_AUTH_URL`, plus existing OAuth client settings. JWT module and AuthService read via `get_settings()`.
- **Alt:** Module-level constants — rejected against AGENT.md hardcoded URL/number rule.

### D6 — `upsert_google_user` commits in the service
- **Keep** the step’s documented exception: auth upsert is always a standalone unit of work; service commits + refreshes. Other domains stay flush-only / caller-commits.

### D7 — Google HTTP resilience
- `httpx.Timeout(connect=5.0, read=10.0)`
- Tenacity: 3 attempts, exponential 1–8s, retry only `TimeoutException` / `ConnectError`
- Never retry 400/401; map to `UnauthorizedError`
- Other HTTP/network failures after retries → `GoogleOAuthError` (502) — named fallback, never raw 500

### D8 — Leave `auth/dependencies.py` as unused stub for now
- Permissions live in `core/security/permissions.py` per blueprint layout. Do not duplicate deps into `auth/dependencies.py` in this change (avoids two sources of truth). Optional cleanup later.

### D9 — Callback failure boundary
- Catch `WandrError` on OAuth callback → redirect `/auth/error?reason=oauth_failed` (never HTML 500). Other endpoints let the global handler emit `ErrorResponse`.

## Risks / Trade-offs

- [Cookie+Bearer dual source] → Prefer header when both present; document in comments
- [Service-level commit] → Document as auth-only exception; do not copy into other services
- [OAuth opt-in empty client id] → `/google` returns `ApiResponse` message instead of redirect (dev-friendly)
- [python-jose maintenance] → Follow step pin; revisit library later if needed
- [No automated OAuth e2e in this change] → Rely on step validation scripts + guest/me/logout curls; full Google flow needs real credentials

## Migration Plan

1. Install deps → implement 1.6 → run JWT validation script
2. 1.7a → schema/exception validation
3. 1.7b → import/instantiation validation
4. 1.7c → wire router → curl guest me / logout / google
5. Update `docs/context.md` (Next step **1.8**)
6. Rollback: revert files + uninstall packages; no DB migration in this change

## Open Questions

- None blocking. If product later needs JS-readable `session_id` cookie, revisit D3 deliberately (security trade-off).
