## 1. Compose mount and restart policy

- [x] 1.1 In `docker-compose.yml`, bind-mount `./.env:/app/.env:ro` on `api`. Keep `env_file: .env` and the `DATABASE_URL` / `QDRANT_URL` / `REDIS_URL` environment overrides. Do not mount `.env` into postgres/qdrant/redis.
- [x] 1.2 Set `restart: unless-stopped` on postgres, qdrant, redis, and api.
- [x] 1.3 Confirm `.dockerignore` still excludes `.env` (keep `!.env.example`).

## 2. Docs

- [x] 2.1 Update `docs/issue_solve.md`: down/up is expected to unbind `:8000` until `wandr_api` is healthy; the permanent compose fix is the `/app/.env` mount; include a down → up proof checklist; keep the optional-`LLM_API_KEY` history.
- [x] 2.2 Note the `.env` mount in `docs/context.md` local quick-ref, `docs/app/system.md` run notes, and `.env.example`.

## 3. Prove restart

- [x] 3.1 `docker compose down` then `docker compose up -d` from `guideagent`. Wait until `wandr_api` is healthy.
- [x] 3.2 Prove `GET /api/v1/health` and `GET /api/v1/destinations/search?q=darjeeling` on host `:8000`. Confirm the container has `/app/.env`.
- [x] 3.3 Playwright: destination search `darjeeling` on the running frontend; API request must be HTTP 200, not connection refused.

## 4. Stop

- [x] 4.1 Do not change destinations/search, CORS, cookies, sibling frontend code, lifespan MiniLM order, or parent tripplanner OpenSpec. Do not commit `.env`.
