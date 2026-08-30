## 1. Production env template

- [x] 1.1 Add `.env.production.example` with all Settings keys from `src/config.py` / `docs/steps/blueprint_production.md` §2 (hosted embeddings, `rediss://` Redis, `postgresql+asyncpg://`, OAuth HTTPS, CORS without trailing slashes, planner timeouts 300/60)
- [x] 1.2 Add comments in template for unused aliases (`EMBEDDING_MODEL`, `UPSTASH_REDIS_REST_TOKEN`, `SUPABASE_*`) and embedding dim cutover (384 → 768)
- [x] 1.3 Ensure `.gitignore` ignores `.env.production` and deploy stamp files (`.deploy-*`) if not already covered

## 2. Docker compose prod wiring

- [x] 2.1 Update `docker-compose.prod.yml`: `image: ${WANDR_IMAGE:-wandr-api:prod}`, remove default `build` on VPS path (optional build block commented for local only)
- [x] 2.2 Pass `WANDR_API_HOST` into Caddy service environment; document in `deploy/Caddyfile` comment

## 3. Ops scripts

- [x] 3.1 Implement `ops/migrate.sh` — `docker run --rm --env-file` + `alembic upgrade head`, `set -euo pipefail`
- [x] 3.2 Implement `ops/deploy.sh` — accept optional image tag, write `.deploy-current-tag` / `.deploy-previous-tag`, `compose pull` + `up -d`
- [x] 3.3 Implement `ops/health.sh` — `curl -fsS` against `https://${WANDR_API_HOST}/api/v1/health`
- [x] 3.4 Implement `ops/status.sh` and `ops/logs.sh` — compose ps / logs wrappers
- [x] 3.5 Implement `ops/rollback.sh` — redeploy prior tag from stamp or argument
- [x] 3.6 Implement `ops/backup.sh` — hosted-provider backup checklist (no secrets to repo)
- [x] 3.7 `chmod +x ops/*.sh` and add brief header comment block in each script (usage, env vars)

## 4. Operator documentation

- [x] 4.1 Update `docs/steps/blueprint_production.md` — reference `.env.production.example`, ops script ordering, link OpenSpec change name
- [x] 4.2 Update `docs/vps.md` — add "Application hosting (next steps)" section (Docker install, clone, env, migrate, deploy, health); note OCI Security List + UFW
- [x] 4.3 Update `docs/ci_cd_plan.md` — mark Phase A done; Phase B-lite in progress with `deploy.yml` + ops hooks

## 5. CI/CD Phase B-lite

- [x] 5.1 Add `.github/workflows/deploy.yml` — build + push `ghcr.io/<owner>/wandr-api:${{ github.sha }}`
- [x] 5.2 Add SSH deploy job: `migrate.sh` → `deploy.sh <sha>` → `health.sh`; start with `workflow_dispatch` only
- [x] 5.3 Document required GitHub Secrets (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `GHCR_*`) in workflow header comment or `docs/ci_cd_plan.md`

## 6. Validation and context

- [x] 6.1 Dry-run locally: `docker build -f Dockerfile .` still passes (CI parity)
- [x] 6.2 Manual proof on VPS (or document in PR): migrate → deploy → health after operator fills `.env.production`
- [x] 6.3 Run `openspec validate production-vps-deploy --strict`
- [x] 6.4 Update `docs/context.md` — deployment row / live endpoints note when first VPS deploy succeeds
