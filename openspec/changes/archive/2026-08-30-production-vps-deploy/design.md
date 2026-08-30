## Context

See `proposal.md`. VPS baseline is done (`docs/vps.md`: 1GB RAM, 2GB swap, amd64, UFW 22/80/443). Production packaging already exists (`Dockerfile`, `docker-compose.prod.yml`, `deploy/Caddyfile`, `docs/steps/blueprint_production.md`). Phase A CI is live (`.github/workflows/ci.yml`). `ops/*.sh` are zero-byte stubs; local `.env` mixes dev localhost URLs with some hosted credentials and wrong field names (`EMBEDDING_MODEL`, Upstash HTTPS REST).

## Goals / Non-Goals

**Goals:**
- Committed `.env.production.example` with correct Settings keys and inline comments (no secrets).
- Thin `ops/*.sh` wrappers callable from SSH and GitHub Actions.
- `docker-compose.prod.yml` supports registry image override + `WANDR_API_HOST` for Caddy.
- Phase B-lite `deploy.yml`: GHCR push + SSH migrate → deploy → health.
- Update operator docs (`blueprint_production.md`, `vps.md`, `ci_cd_plan.md` status).

**Non-Goals:**
- Application code changes (no new endpoints, no Settings refactor).
- Staging environment, blue/green, Terraform.
- Building images on the 1GB VPS.
- Alembic downgrade automation.
- Frontend deploy pipeline.

## Decisions

### 1. Two env files: `.env` (local) vs `.env.production` (VPS only)

**Choice:** Keep `.env` for local docker-compose dev; add `.env.production.example` as the committed template. Real `.env.production` lives only on the VPS (and in GitHub Secrets for CI migrate if needed).

**Rationale:** Avoids comment/uncomment collisions discovered in explore. Matches `.env.example` pattern and `.dockerignore` exclusion.

**Alternative rejected:** Single file with commented prod blocks — error-prone when flipping URLs.

### 2. Ops scripts as bash + `set -euo pipefail`

**Choice:** POSIX-ish bash scripts in `ops/` with shared conventions:
- `COMPOSE_FILE=docker-compose.prod.yml`
- `ENV_FILE` default `.env.production` (override via `WANDR_ENV_FILE`)
- `IMAGE` default `wandr-api:prod` or `ghcr.io/<owner>/wandr-api:<tag>` via `WANDR_IMAGE`

**Rationale:** `docs/ci_cd_plan.md` already names these scripts as the CD executor; bash works on Ubuntu VPS without extra deps.

**Script responsibilities:**

| Script | Action |
|--------|--------|
| `migrate.sh` | `docker run --rm --env-file $ENV_FILE $IMAGE alembic upgrade head` |
| `deploy.sh` | Write `.deploy-tag` stamp; `compose pull` if registry; `compose up -d` |
| `health.sh` | `curl -fsS https://$WANDR_API_HOST/api/v1/health` |
| `status.sh` | `compose ps` |
| `logs.sh` | `compose logs -f --tail=100 api caddy` |
| `rollback.sh` | Read `.deploy-tag` or arg; redeploy prior SHA |
| `backup.sh` | Echo provider backup checklist (Supabase/Qdrant dashboards); optional `pg_dump` only if operator sets `DATABASE_URL` locally — no auto dump to repo |

### 3. Compose prod: image from env, not build on VPS

**Choice:** Update `docker-compose.prod.yml`:

```yaml
api:
  image: ${WANDR_IMAGE:-wandr-api:prod}
  # build: only for local manual testing; CI/CD sets WANDR_IMAGE to GHCR
```

Caddy gets `environment: WANDR_API_HOST: ${WANDR_API_HOST}`.

**Rationale:** 1GB VPS OOM on `docker build`. amd64 matches CI `ubuntu-latest`.

### 4. `.env.production.example` content highlights

Must fix explore findings explicitly in comments:
- `REDIS_URL=rediss://default:<token>@<host>:6379` (from Upstash **Redis** tab, not REST URL)
- Remove/document that `UPSTASH_REDIS_REST_TOKEN` is unused by app
- `PLACES_EMBEDDING_BACKEND=hosted`, `PLACES_EMBEDDING_MODEL=gemini/text-embedding-004`, `PLACES_EMBEDDING_DIM=768`
- `DATABASE_URL=postgresql+asyncpg://...` (Supabase: direct connection or pooler note)
- `QDRANT_URL=https://...` (fix typo `QDRENT`)
- `PLANNER_GENERATION_TIMEOUT_SECONDS=300`, `LLM_TIMEOUT_SECONDS=60`
- `CORS_ALLOWED_ORIGINS=["https://tripai-stagging.vercel.app"]` (no trailing slash)
- `GOOGLE_REDIRECT_URI=https://api.<host>/api/v1/auth/callback`
- `ENVIRONMENT=production`, `DEBUG=false`

### 5. Phase B-lite GitHub Actions

**Choice:** New `.github/workflows/deploy.yml`:
- `on: workflow_dispatch` + `on: push: branches: [main]` with `paths-ignore` optional later
- Jobs: `ci-gate` (reuse or require success of test job — simplest: run test + docker-build inline or use `workflow_run` after ci — **prefer `workflow_dispatch` + manual first**, then enable push after secrets configured)
- `build-push`: login GHCR, build, push `ghcr.io/${{ github.repository_owner }}/wandr-api:${{ github.sha }}`
- `deploy`: appleboy/ssh-action or native ssh — secrets: `VPS_HOST`, `VPS_SSH_KEY`, `VPS_USER`, `GHCR_TOKEN` on VPS for pull

**Rationale:** User wants CI/CD soon but VPS secrets aren't wired yet. `workflow_dispatch` allows testing before auto-deploy on every merge.

**Alternative:** Deploy only on git tag — deferred; SHA tags sufficient for testing.

### 6. Deploy stamp for rollback

**Choice:** `ops/deploy.sh` writes `.deploy-previous-tag` and `.deploy-current-tag` in repo dir on VPS (gitignored via `.deploy-*` pattern in root `.gitignore` if needed).

**Rationale:** Single-host compose; no k8s rollout history.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Wrong Redis URL format (HTTPS REST) | Template comments + example `rediss://` |
| Embedding dim mismatch (384 vs 768) | Blueprint §5 + example env; reindex task in tasks |
| Supabase `postgresql://` without asyncpg | Example uses `postgresql+asyncpg://` |
| OCI Security List vs UFW | Document both in `vps.md` |
| SSH deploy exposes secrets in logs | Scripts never `echo` env files; GH Actions masked secrets |
| Migrate-before-deploy breaks on bad migration | Deploy job aborts; old containers keep running until `up` |
| 1GB RAM under concurrent generate | swap already enabled; workers=1 in Dockerfile |

## Migration Plan

1. Apply change: add `.env.production.example`, implement `ops/*.sh`, tweak compose.
2. On VPS: `git clone` or scp repo; `cp .env.production.example .env.production`; fill secrets from hosted consoles.
3. Set DNS + `WANDR_API_HOST`; update Google OAuth redirect + CORS.
4. First deploy: `ops/migrate.sh` → reindex if needed → `ops/deploy.sh` → `ops/health.sh`.
5. Configure GHCR + SSH secrets; test `workflow_dispatch` deploy.
6. Enable auto-deploy on `main` when comfortable.

**Rollback:** `ops/rollback.sh <previous-sha>` + manual DB restore only if migration was destructive (out of scope for auto downgrade).

## Open Questions

- Exact API hostname (`api.tripai...` vs IP-only TLS via Caddy on-demand) — operator fills in `.env.production` and Caddyfile before first deploy.
- GHCR package name / org — use `github.repository_owner` in workflow; confirm on first push.
- Supabase connection: direct vs pooler for asyncpg — document both in example comments; operator picks one.
