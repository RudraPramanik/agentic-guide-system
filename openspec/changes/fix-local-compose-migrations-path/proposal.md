## Why

Local Compose `wandr_api` crash-loops on `alembic upgrade head` (`FAILED: Path doesn't exist: migrations`), so host `:8000` never binds and the sibling frontend cannot load `GET /api/v1/places` (or any catalog route). Production already copies `migrations/` and stays healthy; local `Dockerfile.dev` and root `docker-compose.yml` still point at the removed `alembic/` scripts directory.

## What Changes

- Point the **local** API image and Compose bind-mounts at `migrations/` (the directory `alembic.ini` already names as `script_location`).
- Keep migrate-then-serve as Compose-only; lifespan still does not auto-migrate.
- Document that a local `.env` copied from production CORS (Vercel-only) blocks `http://localhost:3000`; `.env.example` must keep the local Next origin. Do not commit `.env`.
- **Non-goals:** Do not change the production `Dockerfile`, `docker-compose.prod.yml`, VPS deploy, `.env.production`, sibling frontend code, endpoints, cookies, or Settings. Do not implement `allow-loopback-cors-origins` (127.0.0.1 default list) in this change. No new packages or env var names.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `local-docker-dev-stack`: Local Compose migrate-then-serve MUST use the same Alembic scripts directory as `alembic.ini` (`migrations/`). After `docker compose up` (rebuild as needed), `GET /api/v1/health` on host `:8000` MUST succeed. Operator docs MUST tell local developers to include the sibling FE origin in `CORS_ALLOWED_ORIGINS` and not to copy a Vercel-only list from production env. Production packaging MUST remain unchanged.

## Impact

- `Dockerfile.dev`, root `docker-compose.yml` (api volumes / COPY)
- `docs/issue_solve.md`, `docs/FE_guide.md` local run notes, `.env.example` CORS comment, `docs/context.md` local quick-ref
- Proof: rebuild local `api`, health + places/search on `:8000`; sibling FE places fetch no longer connection-refused
- Production `Dockerfile` (`COPY migrations ./migrations`) and VPS remain as-is
- Parent tripplanner OpenSpec out of scope; sibling frontend unchanged
- AGENT.md: compose/Dockerfile.dev change is in scope because this change explicitly requires it; still no `os.environ.get()` in app code
