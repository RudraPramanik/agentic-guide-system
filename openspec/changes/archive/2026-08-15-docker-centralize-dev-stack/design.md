## Context

See proposal.md — Why. Today root `docker-compose.yml` is PostGIS (`5433:5432`) + Qdrant (`6335:6333`). Uvicorn runs on the host. Production already has a slim `Dockerfile` + `docker-compose.prod.yml` (API + Caddy, hosted data plane). `get_settings()` loads `.env`; empty `REDIS_URL` keeps in-memory rate limit + planner cache. Host pytest and scripts expect published localhost ports. The `alembic/` package directory shadows `python -m alembic` on the host; the image console script `alembic` is the in-container invoke.

No application architecture change (router → service → repository). Compose injects env; app code still uses `get_settings()` only.

## Goals / Non-Goals

**Goals:**

- One Compose command starts PostGIS, Qdrant, Redis, and uvicorn with reload on `:8000`.
- Keep host pytest/scripts/optional host uvicorn working via published ports and unchanged host `.env` URLs.
- Leave production packaging (`Dockerfile`, `docker-compose.prod.yml`, migrate-outside-lifespan) unchanged.

**Non-Goals:**

- Frontend container; Nominatim/Overpass/OSRM self-host; pytest-in-Compose as default; new Python packages; API/schema changes.

## Decisions

### D1 — Extend root compose; do not merge prod compose

Add `api` + `redis` to root `docker-compose.yml`. Keep `docker-compose.prod.yml` API+Caddy only.

**Alternatives:** Separate `docker-compose.dev.yml` — rejected (today’s muscle memory is `docker compose up`; extra `-f` fights “single command”). Put data services on the VPS — rejected (production-deployment-blueprint).

### D2 — `Dockerfile.dev` + bind mounts, not the prod image

Local image: `python:3.12-slim`, `PYTHONPATH=/app`, install `requirements.txt` (MiniLM path). Bind-mount `src`, `alembic`, `scripts`, `alembic.ini`. Hugging Face cache volume for MiniLM so cold starts do not re-download.

Prod `Dockerfile` stays `requirements-prod.txt` / no torch.

**Alternatives:** Reuse prod image locally — rejected (breaks `PLACES_EMBEDDING_BACKEND=local`). Multi-stage one Dockerfile with targets — acceptable later; two files match current prod/dev split. Default PyPI torch on Linux pulls CUDA — **CPU torch** (`https://download.pytorch.org/whl/cpu`) is installed in `Dockerfile.dev` so MiniLM works without a multi-GB CUDA image.

### D3 — Compose `environment:` wins over `env_file` for URLs

```
env_file: .env
environment:
  DATABASE_URL: postgresql+asyncpg://wandr:wandr@postgres:5432/wandr
  QDRANT_URL: http://qdrant:6333
  REDIS_URL: redis://redis:6379/0
```

Host `.env` stays `localhost:5433` / `localhost:6335` / empty Redis. Do not bake `.env` into the image (`.dockerignore` already excludes it).

Redis host publish: **6380:6379** (avoid host Redis on 6379). API **8000:8000**. Postgres/Qdrant ports unchanged.

**Alternatives:** Ask developers to maintain a second `.env.docker` — rejected (drift). `extra_hosts: host.docker.internal` so the container uses host `.env` URLs — rejected (API would miss compose DNS and depend on published ports).

### D4 — Compose command: migrate then reload uvicorn (not lifespan)

```
alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Use the image `alembic` console script (not `python -m alembic`). Prefer Compose `command:` over a `.sh` entrypoint so Windows CRLF cannot break the script. `--reload` implies a single process (no `--workers`).

`depends_on` postgres `service_healthy`; qdrant/redis `service_started` (add cheap healthchecks if cheap). API healthcheck: in-process HTTP GET `/api/v1/health` (slim image may lack curl).

**Alternatives:** Migrate in FastAPI lifespan — rejected (production contract + AGENT/blueprint). Manual host alembic before compose — rejected (not one command).

### D5 — Scripts via `docker compose exec api`; pytest stays on host

Document:

```
docker compose exec api python scripts/seed_destination.py --destination "Darjeeling" --radius 30
```

Host `python scripts/...` remains valid against published ports. Do not add a pytest service.

### D6 — Docs delta only

- `docs/context.md` Local dev quick ref → `docker compose up --build` as the default API start; keep host uvicorn as optional.
- `docs/steps/blueprint_production.md` “dev compose” sentence: local stack is PostGIS + Qdrant + Redis + API, still not the VPS data plane.
- Touch `docs/FE_guide.md` / `docs/app/system.md` only where they still say compose is data-only.

## Risks / Trade-offs

- **[Windows bind-mount / reload flakiness]** → Document Docker Desktop file sharing; fallback remains host uvicorn + `docker compose up` for data services only.
- **[First MiniLM download is slow / large image]** → HF cache volume; hosted embeddings still work in the same image via env.
- **[Alembic shadowing on host]** → Container uses console script; do not tell developers to `python -m alembic` inside the API container either if `/app/alembic` is a package dir — use `alembic` on PATH.
- **[Compose Redis vs empty host REDIS_URL]** → API container gets Redis; host pytest stays in-memory. Document optional host `REDIS_URL=redis://localhost:6380/0`.
- **[Port 8000 already used by host uvicorn]** → Document stopping host uvicorn before `compose up`; healthcheck failure is the signal.
- **[Secrets in `env_file: .env`]** → File stays on host, not in the image; do not commit `.env`.

## Migration Plan

1. Add `Dockerfile.dev` and compose services; do not change prod files except the blueprint sentence.
2. Developers: `docker compose down` then `docker compose up --build`. Existing PostGIS/Qdrant volumes reuse; Redis volume is new; API runs `alembic upgrade head` (idempotent).
3. Rollback: remove `api`/`redis` from compose (or checkout previous compose); run host uvicorn as today. Data volumes unchanged.

## Open Questions

None. Frontend-in-Docker and pytest-in-Compose are deferred and do not affect this spec or task list.
