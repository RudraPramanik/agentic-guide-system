## Context

See `proposal.md` for why. `alembic.ini` already has `script_location = migrations`. Host tree is `migrations/` (no `alembic/` scripts dir). Production `Dockerfile` already `COPY migrations ./migrations`. Local `Dockerfile.dev` still `COPY alembic ./alembic`; Compose still bind-mounts `./alembic:/app/alembic` and host `alembic.ini`. Compose command runs `alembic upgrade head` then uvicorn. Specs: `specs/local-docker-dev-stack/spec.md`.

## Goals / Non-Goals

**Goals:**

- Local image + live bind-mounts expose `/app/migrations` so Alembic matches `alembic.ini`.
- Operators can rebuild Compose `api` and get a healthy `:8000` without touching VPS packaging.
- Local CORS trap is documented; `.env.example` stays laptop-safe.

**Non-Goals:**

- Changing production `Dockerfile` / prod compose / `.env.production`.
- Renaming `script_location` back to `alembic/`.
- Editing `src/config.py` CORS defaults or shipping `allow-loopback-cors-origins`.
- Committing gitignored `.env`.
- Sibling frontend or new endpoints.

## Decisions

### 1. Align local COPY and volume with `migrations/`; leave production Dockerfile alone

**Choice:** In `Dockerfile.dev`, copy `migrations/` the same way production does (`COPY migrations ./migrations`). In `docker-compose.yml` `api` volumes, replace `./alembic:/app/alembic` with `./migrations:/app/migrations`. Keep `./alembic.ini:/app/alembic.ini:ro`. Do not edit production `Dockerfile`.

**Why:** Alembic reads `script_location` from the bind-mounted ini. The crash is a missing directory, not a Settings or lifespan bug. Production already has the correct COPY; changing it would violate the “VPS remains as-is” constraint.

**Alternative considered:** Change `alembic.ini` back to `script_location = alembic` and restore an `alembic/` folder. Rejected — the rename exists so a package dir named `alembic` does not shadow the Alembic CLI; production already uses `migrations/`.

**Alternative considered:** Drop the Compose bind-mount and rely on image COPY only. Rejected — local reload workflow bind-mounts source; migrations would go stale without a rebuild on every revision.

### 2. Keep migrate-then-serve and PYTHONPATH as they are

**Choice:** Leave the Compose `command` (`alembic upgrade head && exec uvicorn … --reload-dir /app/src`) and the site-packages-first `PYTHONPATH` prefix unchanged.

**Why:** The failure is path presence, not CLI shadowing, once `alembic/` is no longer mounted. Lifespan must still not auto-migrate.

**Alternative considered:** Move migrate out of Compose. Rejected — existing `local-docker-dev-stack` contract is Compose-only migrate-then-serve.

### 3. CORS: document and example env only

**Choice:** Keep `.env.example` as `CORS_ALLOWED_ORIGINS=["http://localhost:3000"]` and add an explicit warning in `docs/issue_solve.md` / `docs/FE_guide.md` not to paste a Vercel-only list into local `.env`. Apply does not edit gitignored `.env`; the operator must add `http://localhost:3000` locally after the API boots.

**Why:** pydantic-settings overrides the code default from `.env`. Fixing compose without that note leaves a second “places not loading” failure (browser CORS). Production allowlist stays on the VPS.

**Alternative considered:** Change `Settings.CORS_ALLOWED_ORIGINS` default or merge origins in code. Rejected — out of scope; overlaps unfinished `allow-loopback-cors-origins`; would not beat an explicit `.env` list anyway.

## Risks / Trade-offs

- [Rebuild required] → `Dockerfile.dev` COPY change needs `docker compose up --build` (or equivalent) so the image is not an old layer with `COPY alembic`.
- [Empty local catalog after API is healthy] → Docs: search + prepare on this PostGIS; do not reuse VPS destination UUIDs. Not a compose path bug.
- [Operator still has Vercel-only CORS in `.env`] → Documented; apply cannot commit the secret file.
- [Windows bind-mount of `migrations/`] → Same pattern as existing `./src` mount; if Desktop file sharing is off, healthcheck still fails — already documented for this stack.

## Migration Plan

From `guideagent/`: rebuild and recreate `api` (`docker compose up --build -d`). Existing PostGIS/Qdrant/Redis volumes stay. Rollback: revert `Dockerfile.dev` and the compose volume line; production deploy paths unused.

## Open Questions

None.
