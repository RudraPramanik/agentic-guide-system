## Why

Local Wandr still splits the stack: `docker compose up -d` starts only PostGIS + Qdrant, then a host Python env must run `uvicorn src.main:app --reload`. That two-step loop drifts from the production Docker API image, blocks “one command” onboarding, and leaves Redis (already in code for rate limit + planner cache) off the local data plane. We need a single Compose command that brings up the full local backend, including uvicorn.

## What Changes

- Extend root `docker-compose.yml` (still **dev-only**) so one command — `docker compose up --build` — starts PostGIS, Qdrant, Redis, and the FastAPI/uvicorn API.
- Add a **dev** API image (`Dockerfile.dev`) that installs `requirements.txt` (MiniLM path remains available), bind-mounts source, and runs uvicorn with `--reload` on `0.0.0.0:8000`.
- Compose **overrides** container `DATABASE_URL` / `QDRANT_URL` / `REDIS_URL` to Docker DNS (`postgres`, `qdrant`, `redis`). Host `.env` keeps `localhost:5433` / `localhost:6335` / empty Redis so host pytest and scripts still work against published ports.
- Optional local entrypoint: `alembic upgrade head` then uvicorn (dev convenience only — **not** app lifespan; production migrate-outside-lifespan contract unchanged).
- Document `docker compose exec api python scripts/...` as the in-stack way to run seed/enrich/index; host scripts remain valid.
- Update `docs/context.md` local quick-ref (and light production-blueprint wording so root compose is still “dev only”, now API+data not PostGIS+Qdrant only).

### Non-goals

- Frontend / Next.js in this compose (sibling repo; `docs/FE_guide.md` unchanged except the local API start command)
- Changing `docker-compose.prod.yml` topology (API + Caddy only; hosted data plane)
- Self-hosting Nominatim, Overpass, or OSRM
- Putting pytest inside the default Compose stack
- Auto-migrate in production app lifespan or multi-worker uvicorn
- New Python packages or application API/schema changes

## Capabilities

### New Capabilities

- `local-docker-dev-stack`: Single-command local Compose stack (PostGIS, Qdrant, Redis, uvicorn API with reload); container vs host env split; published ports for host tools.

### Modified Capabilities

- `production-deployment-blueprint`: Local compose remains development-only, but the documented root stack is no longer “PostGIS + Qdrant only” — it includes the local API (and Redis) while still MUST NOT be the production data plane.

## Impact

- **Ops / Docker:** `docker-compose.yml`, new `Dockerfile.dev`, optional `docker/entrypoint.dev.sh`, `.dockerignore` (do not break prod image), `.env.example` comments for compose vs host URLs.
- **Code:** No router/service/repository or endpoint changes. Settings still via `get_settings()`; Compose injects env.
- **AGENT.md:** No new packages; no `os.environ.get()` in app code; LLM/geo/travel_engine rules untouched; production migrate-not-in-lifespan stays.
- **Docs:** `docs/context.md` Local dev quick ref; `docs/steps/blueprint_production.md` “dev compose” sentence; optional one-line notes in `docs/FE_guide.md` / `docs/app/system.md` if they still say compose is data-only.
- **Stubs:** None of the remaining stubs (evaluation HTTP, `src/auth/dependencies.py`) are touched.
- **Not a numbered P1–P7 step** — post-P7 operator/dev-ergonomics change.
