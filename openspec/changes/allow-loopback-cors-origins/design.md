## Context

See `proposal.md` for why. Guest `GET /trips/{id}` is optional auth; 403 is `TripService.assert_can_access` (`wandr_session` vs `Trip.session_id`). Cookies are `SameSite=Lax`, httpOnly, set by auth `/me` and planner generate. Sibling FE `credentials: "include"` is already correct. Default CORS today is only `http://localhost:3000`. Sibling FE local API URL is often `http://127.0.0.1:8000` (Docker/IPv6). `localhost` vs `127.0.0.1` are different sites for cookies.

## Goals / Non-Goals

**Goals:**

- Default CORS allowlist includes both local Next origins so operators can use either loopback spelling **as a matched pair** with the API host.
- Tests prove both origins receive `Access-Control-Allow-Origin` under defaults.
- FE_guide states the host-pair rule so CORS is not mistaken for a cookie-merge.

**Non-Goals:**

- Changing `assert_can_access`, generate session minting, or cookie flags.
- Runtime rewrite of `NEXT_PUBLIC_API_URL` (sibling FE already forbids that).
- Same-origin Next proxy / BFF.
- Production CORS defaults (prod still sets explicit HTTPS origins).

## Decisions

### 1. Extend the default list; do not add `*`

**Choice:** `CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]` in `src/config.py`. Same JSON list in `.env.example`.

**Why:** Star + credentials is forbidden. Both origins are local-only and already used in practice. Settings remain the single source; `main.py` stays origin-agnostic.

**Alternative considered:** Document-only “set CORS yourself.” Rejected — the 127.0.0.1 FE origin is the documented Docker path and currently fails CORS, which pushes operators onto mixed hosts.

### 2. Keep SameSite=Lax (Option A)

**Choice:** No cookie attribute changes.

**Why:** Mixed `localhost` / `127.0.0.1` is cross-site; Lax correctly withholds the cookie. `SameSite=None` needs `Secure` and is Option B, deferred. Ownership 403 is the right signal.

**Alternative considered:** Relax guest 403 when cookie missing. Rejected — IDOR / session fixation.

### 3. Docs in FE_guide, not a new env var

**Choice:** Spell the two valid pairs in `docs/FE_guide.md` §4–5. No new settings key.

**Why:** The trap is operator host choice. A third env var would not set the browser URL bar.

## Risks / Trade-offs

- [Operators still mix `localhost:3000` with API `127.0.0.1:8000`] → Mitigation: guide + existing FE host-mismatch hint; CORS change does not claim to fix mixed hosts.
- [Local `.env` already pins CORS to only localhost] → Mitigation: `.env.example` shows both; operators with a pinned list must add `http://127.0.0.1:3000` themselves if they browse that origin.
- [Wider local allowlist] → Mitigation: both origins are loopback HTTP only; prod checklist still requires explicit HTTPS origins.

## Migration Plan

Deploy with the API process (settings default). Rollback: revert the two-origin default. No DB migration. Existing production `CORS_ALLOWED_ORIGINS` env overrides are unchanged.

## Open Questions

None.
