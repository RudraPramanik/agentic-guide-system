## Why

Staging FE (`https://tripai-stagging.vercel.app`) and API (`https://api.exporaai.xyz`) are different sites. Cookies use `SameSite=Lax`, so credentialed cross-origin fetch/SSE do not send `wandr_session` / `wandr_token`. Guests get trip 403 “different session”; `/auth/done` cannot confirm login.

## What Changes

- When `ENVIRONMENT=production`, set `wandr_token` and `wandr_session` with `SameSite=None` and `Secure=True`.
- Non-production keeps `SameSite=Lax` (local same-host MVP).
- Align planner generate session cookie and logout `delete_cookie` flags.
- Document staging FE↔API cookie requirement in production blueprint / FE guide pointer.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `auth-domain`: Production cookie SameSite policy for cross-origin SPA.
- `planner-sse-generate`: Generate `wandr_session` cookie flags match auth in production.

## Impact

- `src/auth/router.py`, `src/planner/router.py`, auth tests, production docs.
- **Deploy:** Must ship a new API image to VPS (env-only change is insufficient).
- Local/dev unchanged (Lax).
- CORS must already list the Vercel origin with credentials (already true for staging).

## Non-goals

- Shared cookie Domain / reverse-proxy same-site topology.
- Changing guest ownership rules.
- FE code changes.
