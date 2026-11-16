## 1. Architecture local-dev section

- [x] 1.1 In `docs/app/system.md` Local Development Infrastructure only, set the `wandr_api` host port to 8001 and note that the container still listens on 8000. Change the health and OpenAPI comments to `http://localhost:8001/api/v1/health` and `http://localhost:8001/docs`. Leave Postgres 5433, Qdrant 6335/6336, and Redis 6380 as they are.

## 2. Agent checkpoint quick ref

- [x] 2.1 In `docs/context.md` local dev quick ref, change the Compose comment and the browser URL from host port 8000 to 8001 (`http://localhost:8001/docs`). Keep the optional host uvicorn line on `--port 8000`, and state that path runs only while the Compose API service is stopped.
- [x] 2.2 In the same section, rewrite the port-clash bullet and the `docker compose down` / `ERR_CONNECTION_REFUSED` bullet so they name host port 8001, not 8000. Do not edit the progress table, stub list, or production-host lines.

## 3. Check

- [x] 3.1 Confirm `docker-compose.yml` still publishes `8001:8000` and was not edited. Grep the local infrastructure section of `docs/app/system.md` and the local dev quick ref of `docs/context.md` and confirm they no longer say Compose publishes or clashes on host port 8000. Do not edit `docs/FE_guide.md`, `docs/issue_solve.md`, `docs/steps/`, or `docs/blueprint_frontend.md`.
