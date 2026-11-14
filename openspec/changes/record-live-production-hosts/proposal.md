## Why

Living operator and agent docs still say the first VPS deploy has not happened and still name retired origins (`api.exporaai.xyz`, `https://tripai-stagging.vercel.app`). As of 2026-11-14 the public site is `https://explorai.online` (HTTP 200) and the API hostname is `api.explorai.online` (DNS via Cloudflare; `exporaai.xyz` is NXDOMAIN). Agents that trust `docs/context.md` will plan a deploy that already occurred and copy a dead frontend origin.

## What Changes

- Record the canonical public hosts in the agent checkpoint and the architecture rollup: site `https://explorai.online` (and `www`), API `https://api.explorai.online`. Replace “next = first VPS deploy” and “Live API URL TBD after first VPS bring-up”.
- Point `docs/vps.md` application-hosting notes at those hosts. Keep the SameSite=None rule only for a frontend on a different site; the live pair shares the registrable domain `explorai.online`, which matches the locked Option A (`SameSite=Lax`) note in `docs/context.md`.
- Update `.env.production.example` public-origin fields (`WANDR_API_HOST`, `GOOGLE_REDIRECT_URI` host, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`) from the retired Vercel preview / `api.example.com` placeholders to the canonical hosts. No secrets.
- Do not freeze a health verdict. A probe on 2026-11-14 got HTTP 503 from `/api/v1/health`, then a body timeout. Docs name the hosts and still send operators to `ops/health.sh` / `/api/v1/health`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-deployment-blueprint`: Operator notes and the committed production env template must name the canonical public hosts and must not describe first VPS bring-up as still pending or cite retired origins as current.

## Impact

- **Scope:** BE-only docs in `guideagent`. Not a numbered `docs/steps/step*.md` build step.
- **Docs:** `docs/context.md` (header, deployment note), `docs/app/system.md` (build-status rollup), `docs/vps.md` (application hosting).
- **Template:** `.env.production.example` public host fields only.
- **Specs:** delta under `production-deployment-blueprint`.
- **Non-goals:** no application code (`src/config.py` CORS default stays, even though it still lists the retired Vercel origin); no edits to `.env.production`; no cookie/CORS behavior change; no claim that Redis or `/health` is green; no rewrite of archived OpenSpec or of `openspec/changes/cross-site-prod-auth-cookies` (that proposal records the old cross-site pair as the bug it addressed); no parent `docs/context` or frontend guide edits (those use placeholders); no Docker, ops scripts, or run-script changes.
- **AGENT.md:** unchanged. No new packages, endpoints, or env var names. `get_settings()` remains the only env path. Stub list in `docs/context.md` (evaluation HTTP, `auth/dependencies.py`) stays as written.
