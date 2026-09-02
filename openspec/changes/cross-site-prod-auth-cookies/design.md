## Context

See proposal.md. Staging uses split hosts; Lax cookies break credentialed cross-site calls. `Secure` already flips on `ENVIRONMENT=production`.

## Goals / Non-Goals

**Goals:** Production cookies work for Vercel → API credentialed requests; keep Lax locally.

**Non-Goals:** CHIPS/Partitioned attribute; Domain= parent cookie sharing; FE changes.

## Decisions

### 1. `SameSite=None` only when production

- Helper `_cookie_samesite()` → `"none"` if `ENVIRONMENT == "production"` else `"lax"`.
- Always pair with `secure=_cookie_secure()` (True in production) — browsers require Secure with None.

### 2. Single helper used by auth + planner

- Export `_cookie_samesite` next to `_cookie_secure`; planner imports both.

### 3. Logout delete_cookie

- Pass matching `samesite` + `secure` so browsers clear the production cookie.

## Risks / Trade-offs

- [Third-party cookie restrictions] → Mitigation: requests target API host; cookies are host-scoped to API; SameSite=None is the standard SPA pattern. Monitor browser policy changes.
- [Local prod ENVIRONMENT mis-set] → Mitigation: only production compose uses ENVIRONMENT=production.

## Migration Plan

1. Ship code to `dev02`, build image off-VPS, load/restart on Oracle.
2. Clear old cookies in browser; re-login / re-generate on staging.
3. Rollback: previous image restores Lax (staging broken again for cookies).
