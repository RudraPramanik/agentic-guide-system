## Why

`allow-catalog-boot-without-llm-key` stopped Alembic from requiring `LLM_API_KEY`, but `docker compose down` then `up` still left sibling FE with `ERR_CONNECTION_REFUSED` on `:8000`. Settings still load `env_file=".env"` from the container cwd (`/app/.env`), which is **not** bind-mounted. Compose `env_file` injection is the only path for host secrets, and it does not survive every Windows recreate the same way a mounted file does. Operators should not re-paste keys after every down/up.

## What Changes

- Bind-mount host `./.env` to `/app/.env:ro` on the local Compose `api` service so `get_settings()` reads the same gitignored file after every recreate.
- Keep Compose `environment` overrides for `DATABASE_URL`, `QDRANT_URL`, and `REDIS_URL` (Docker DNS). Host `.env` localhost ports MUST NOT win inside the container.
- Keep `env_file: .env` as a second injection path.
- Set `restart: unless-stopped` on local Compose services so Docker Desktop restarts recover the API (does not replace an explicit `compose down`).
- Document in `docs/issue_solve.md` that `compose down` unbinds `:8000` until `up` finishes; prove with a down → up cycle (health + destinations/search).
- **Non-goals:** Do not commit `.env`. Do not change destinations/search, CORS, cookies, sibling frontend, production compose, or make `SECRET_KEY` / `DATABASE_URL` / `NOMINATIM_USER_AGENT` optional. Do not move MiniLM off lifespan in this change (still fail-soft, still awaited). No new packages or env var names. All env still via `get_settings()`.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `local-docker-dev-stack`: The local API container MUST see the host Compose `.env` at `/app/.env` after recreate. Host published-port URLs in that file MUST remain overridden by in-compose DNS for Postgres/Qdrant/Redis. After `docker compose down` then `up`, `GET /api/v1/health` and destinations search on host `:8000` MUST succeed without re-editing `.env`.

## Impact

- `docker-compose.yml` (api volumes + restart policy)
- `docs/issue_solve.md`, `docs/context.md` local quick-ref, `docs/app/system.md` run notes
- `.env.example` comment that Compose mounts `.env` into `/app/.env`
- AGENT.md: still no `os.environ.get()` in app code; no new packages
- Proof: compose down, compose up, health + search; Playwright on sibling FE
- Parent tripplanner OpenSpec out of scope
