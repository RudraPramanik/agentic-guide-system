## Why

OAuth callback success left users on the API JSON page. Frontend login UX requires redirect to `{FRONTEND_URL}/auth/done` after Set-Cookie, with failures on `{FRONTEND_URL}/auth/error`.

## What Changes

- Add `FRONTEND_URL` to Settings
- Callback success → redirect to `{FRONTEND_URL}/auth/done` with `wandr_token`
- Callback failure → redirect to `{FRONTEND_URL}/auth/error?reason=…`
- JSON fallback when `FRONTEND_URL` empty (local debug)
- Tests for redirect + cookie behavior

## Capabilities

### Modified Capabilities

- `auth-domain`: OAuth callback redirect behavior

## Impact

- `src/config.py`, `src/auth/router.py`, `tests/auth/test_auth_router.py`, `docs/FE_guide.md`, `.env.example`
