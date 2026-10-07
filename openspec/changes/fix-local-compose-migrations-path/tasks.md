## 1. Local image and Compose volumes

- [x] 1.1 In `Dockerfile.dev`, replace `COPY alembic ./alembic` with `COPY migrations ./migrations` (same layout as production `Dockerfile`). Do not edit production `Dockerfile`.
- [x] 1.2 In `docker-compose.yml` `api` volumes, replace `./alembic:/app/alembic` with `./migrations:/app/migrations`. Keep `./alembic.ini:/app/alembic.ini:ro`, `./src`, `./scripts`, and `./.env` mounts. Do not change the migrate-then-serve `command` or `PYTHONPATH` prefix.
- [x] 1.3 Confirm `alembic.ini` still has `script_location = migrations` (no revert to `alembic`).

## 2. Operator docs (local CORS + boot)

- [x] 2.1 In `docs/issue_solve.md`, add the missing-`migrations` crash loop (`alembic upgrade head` before uvicorn) as a local-only cause of FE `ERR_CONNECTION_REFUSED` on `:8000`. State the fix is `Dockerfile.dev` + Compose volume alignment; production image already copies `migrations/`.
- [x] 2.2 In the same issue notes (and `docs/FE_guide.md` local CORS row if needed), warn that a Vercel-only `CORS_ALLOWED_ORIGINS` in local `.env` blocks `Origin: http://localhost:3000` after the API is healthy. Do not commit `.env`. Do not change `.env.production`.
- [x] 2.3 Confirm `.env.example` keeps `CORS_ALLOWED_ORIGINS=["http://localhost:3000"]` and add a one-line comment not to copy production-only origins into laptop `.env`. Note the Compose migrations volume in `docs/context.md` local quick-ref if that section still mentions `alembic/`.

## 3. Prove local stack

- [x] 3.1 From `guideagent/`, `docker compose up --build -d` and wait until `wandr_api` is healthy (not Restarting). Logs MUST NOT show `Path doesn't exist: migrations`.
- [x] 3.2 Prove `GET /api/v1/health` on host `:8000`. Prove `GET /api/v1/places?destination_id=` and/or `GET /api/v1/destinations/search` connect (200, 404, or validation JSON — not connection refused).
- [x] 3.3 Confirm production `Dockerfile` still contains `COPY migrations ./migrations` unchanged.

## 4. Stop

- [x] 4.1 Do not change sibling frontend, Settings, cookies, endpoints, `src/config.py` CORS defaults, `allow-loopback-cors-origins`, VPS compose, or parent tripplanner OpenSpec. Do not commit `.env`.
