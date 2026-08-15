## 1. Dev API image

- [x] 1.1 Add `Dockerfile.dev`: `python:3.12-slim`, `PYTHONPATH=/app`, install `requirements.txt`, copy `alembic.ini` / `alembic` / `src` / `scripts`
- [x] 1.2 Default CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` (no `--workers` with reload)
- [x] 1.3 Confirm `.dockerignore` still excludes `.env` / `.venv` / tests junk and does not break the prod `Dockerfile` build

## 2. Compose stack

- [x] 2.1 Add `redis` service to root `docker-compose.yml` (named volume; publish `6380:6379`; cheap healthcheck)
- [x] 2.2 Add `api` service: build `Dockerfile.dev`, `env_file: .env`, override `DATABASE_URL` / `QDRANT_URL` / `REDIS_URL` to compose DNS (`postgres:5432`, `qdrant:6333`, `redis:6379`)
- [x] 2.3 Bind-mount `src`, `alembic`, `scripts`, `alembic.ini`; add Hugging Face cache volume; publish `8000:8000`
- [x] 2.4 `depends_on` postgres `service_healthy` (qdrant/redis started or healthy); `command:` `alembic upgrade head && uvicorn ... --reload` using the image console script, not `python -m alembic`
- [x] 2.5 API healthcheck against `GET /api/v1/health` without assuming curl is in the slim image
- [x] 2.6 Leave `docker-compose.prod.yml` and production `Dockerfile` topology unchanged (API + Caddy; hosted data plane)

## 3. Env comments and docs

- [x] 3.1 Comment `.env.example`: host tools use `localhost:5433` / `:6335` / empty `REDIS_URL`; Compose API service overrides to internal DNS; optional host Redis `redis://localhost:6380/0`
- [x] 3.2 Update `docs/context.md` Local dev quick ref: default `docker compose up --build`; host uvicorn remains optional; `docker compose exec api python scripts/...` for in-stack seed/enrich/index
- [x] 3.3 Update `docs/steps/blueprint_production.md` so root compose is still **dev-only**, now PostGIS + Qdrant + Redis + API (not the VPS data plane)
- [x] 3.4 Fix leftover “compose is PostGIS+Qdrant only” lines in `docs/FE_guide.md` / `docs/app/system.md` if still present

## 4. Proof and context stamp

- [x] 4.1 `docker compose up --build` from repo root → postgres healthy, qdrant/redis up, API healthy; `GET http://localhost:8000/api/v1/health` 200
- [x] 4.2 Confirm host `python -m pytest tests/ -v` still reaches `:5433` / `:6335` with existing `.env` (in-memory Redis)
- [x] 4.3 Confirm `docker-compose.prod.yml` still has no PostGIS/Qdrant/Redis services
- [x] 4.4 Stamp `docs/context.md` Last updated / Current state one-liner for the Docker-centralized local stack
