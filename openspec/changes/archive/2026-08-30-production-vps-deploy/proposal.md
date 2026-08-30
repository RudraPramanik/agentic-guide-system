## Why

The Oracle Free Tier VPS is hardened (swap, UFW, amd64) and hosted services (PostGIS, Qdrant, Redis, LLM, embeddings) are provisioned, but production bring-up still depends on ad-hoc commands and an incomplete local `.env` hybrid. Empty `ops/*.sh` stubs and no committed `.env.production` template block a repeatable first deploy and the Phase B-lite CI/CD path described in `docs/ci_cd_plan.md`.

## What Changes

- Add `.env.production.example` — committed checklist with correct `Settings` field names (`PLACES_EMBEDDING_*`, `rediss://` Redis, `postgresql+asyncpg://`, hosted Qdrant) and no secrets.
- Implement `ops/*.sh` for migrate, deploy, health, status, logs, rollback, and backup — thin wrappers around `docker compose -f docker-compose.prod.yml` and one-off `docker run` for Alembic/scripts.
- Wire `docker-compose.prod.yml` to use `WANDR_API_HOST` for Caddy and document VPS layout in `docs/vps.md` (operator notes only; secrets stay on server).
- Add GitHub Actions **Phase B-lite** workflow: build + push to GHCR on `main`, optional SSH deploy using `ops/deploy.sh` + `ops/health.sh` (manual approval or `workflow_dispatch` for first iterations).
- Document embedding dim cutover (384 → 768) and smoke checklist hooks in ops scripts.
- **Non-goals:** Terraform/IaC, blue/green, staging environment, self-hosted DB/Qdrant on VPS, frontend deploy, changing application runtime code paths.

## Capabilities

### New Capabilities

- `production-ops-scripts`: Shell operators for VPS deploy, migrate, health smoke, logs, status, rollback, and backup — executable contract for manual ops and CI/CD SSH steps.

### Modified Capabilities

- `production-deployment-blueprint`: Extend operator SOP to require `.env.production.example`, ops script usage, and first-deploy ordering (migrate before `compose up`, reindex after dim cutover).
- `github-actions-ci`: Add Phase B-lite CD workflow (registry publish + deploy hook) without removing Phase A test/build gates.

## Impact

- **Files:** `.env.production.example`, `ops/*.sh`, `docker-compose.prod.yml` (env/host wiring), `.github/workflows/deploy.yml` (new), `docs/vps.md`, `docs/ci_cd_plan.md` (status note), `docs/steps/blueprint_production.md` (cross-links).
- **Systems:** Oracle VPS (`docker-compose.prod.yml`), GHCR, hosted PostGIS/Qdrant/Upstash, Google OAuth redirect + CORS for staging FE.
- **AGENT.md constraints:** No new Python packages; no `os.environ` bypass; no router/DB violations; secrets never committed; `docker-compose.yml` remains dev-only.
- **Breaking:** Operators must use `rediss://` (not Upstash HTTPS REST) for `REDIS_URL` and `PLACES_EMBEDDING_*` (not `EMBEDDING_MODEL`) in production env.
