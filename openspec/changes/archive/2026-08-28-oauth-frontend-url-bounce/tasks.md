## Context

Parent change `google-auth-login-signup`. Router already set cookies on JSON response.

## Decisions

- `FRONTEND_URL: str = "http://localhost:3000"` in Settings via `get_settings()` only
- Helper `_frontend_auth_url()` builds absolute redirect targets; empty `FRONTEND_URL` preserves legacy JSON/error paths

## 1. Implementation

- [x] 1.1 Add `FRONTEND_URL` to config + `.env.example`
- [x] 1.2 Update auth router redirects
- [x] 1.3 Add router tests
- [x] 1.4 Update `FE_guide.md` §11
