## Context

See `proposal.md` for why. `get_settings()` uses pydantic-settings `env_file=".env"` (cwd `/app` in the API image). Compose already injects `env_file: .env` and overrides data-plane URLs. Host `.env` is gitignored and listed in `.dockerignore`. `LLM_API_KEY` is already optional at boot (`allow-catalog-boot-without-llm-key`). MiniLM load is fail-soft but still awaited in lifespan — out of scope here.

## Goals / Non-Goals

**Goals:**

- Same host `.env` is what Settings reads after every compose recreate.
- Docker DNS overrides still win for DB / Qdrant / Redis.
- `docs/issue_solve.md` covers down/up so CONNECTION_REFUSED is not treated as a lost code fix.
- Proof is a real `down` then `up`, not only `restart`.

**Non-Goals:**

- Background MiniLM / changing lifespan order.
- Committing `.env` or copying secrets into the image.
- Production `docker-compose.prod.yml`.
- Frontend / CORS / cookie / endpoint changes.

## Decisions

### 1. Bind-mount `.env` rather than COPY it

**Choice:** `./.env:/app/.env:ro` on `api`. Keep `.dockerignore` excluding `.env`.

**Why:** Settings always looks at `.env` relative to cwd. A recreate without a mount leaves `/app/.env` missing and relies only on Compose env injection. A mount is restart-stable and matches `get_settings()` without `os.environ.get()`.

**Alternative considered:** Drop `env_file=".env"` from Settings and use environment-only. Rejected — host pytest and scripts rely on the file; AGENT.md wants a single Settings path.

### 2. Keep Compose `environment` URL overrides

**Choice:** Do not remove `DATABASE_URL` / `QDRANT_URL` / `REDIS_URL` in `docker-compose.yml`.

**Why:** Pydantic prefers environment variables over the env file. Compose `environment` must keep winning so the mounted host file’s `localhost:5433` does not break in-container connections.

**Alternative considered:** Rewrite host `.env` to Docker DNS. Rejected — host pytest needs published ports.

### 3. `restart: unless-stopped`

**Choice:** Apply to postgres, qdrant, redis, and api.

**Why:** Docker Desktop restart is a common “the fix disappeared” report. Explicit `compose down` still stops services; docs will say to `up` again.

## Risks / Trade-offs

- [Missing host `.env` fails the mount] → Mitigation: operators copy `.env.example`; Compose already required that file via `env_file`.
- [Windows path / CRLF] → Mitigation: file stays on the host; UTF-8 without BOM is already the local file.
- [Secrets visible in `docker inspect`] → Mitigation: same as today’s `env_file`; still gitignored.

## Migration Plan

No DB migration. `docker compose up -d` recreates `api` with the new volume. Rollback: remove the `.env` mount and restart policies.

## Open Questions

None.
