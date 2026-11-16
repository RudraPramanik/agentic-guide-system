## Why

`docker-compose.yml` publishes the API as `8001:8000`, but the living local-dev notes and the `local-docker-dev-stack` spec still tell people the host port is 8000. Opening `http://localhost:8000` against Compose fails, and the quick-ref troubleshooting still says to free port 8000 before `docker compose up`.

## What Changes

- Record the split that Compose already implements: uvicorn inside the container stays on `0.0.0.0:8000`; the published host port is **8001**.
- Update `docs/app/system.md` local infra (table row, health URL, OpenAPI URL) and the `docs/context.md` local-dev quick ref, including the port-clash and “compose down unbinds” bullets, so host URLs are `http://localhost:8001`.
- Replace the `local-docker-dev-stack` requirement that host port 8000 must be published. Reload, Postgres-healthy wait, and the other published ports (5433 / 6335 / 6336 / 6380) stay.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `local-docker-dev-stack`: The API container still binds uvicorn to port 8000 with reload. The published host port MUST be 8001, and the living local-dev docs MUST use `http://localhost:8001` for health and OpenAPI. Host port 8000 is no longer the Compose contract.

## Impact

- **Scope:** BE-only docs in `guideagent`. Not a numbered `docs/steps/step*.md` build step.
- **Docs:** `docs/app/system.md` (Local Development Infrastructure only), `docs/context.md` (local dev quick ref and the two `:8000` troubleshooting bullets in that section).
- **Specs:** delta under `local-docker-dev-stack`. The current requirement “published port 8000” conflicts with `docker-compose.yml`; this change follows the compose file.
- **Code:** none. `docker-compose.yml` already maps `8001:8000`. Container healthcheck stays on `127.0.0.1:8000`.
- **Non-goals:** no edit to `docker-compose.yml`, Dockerfiles, or run scripts; no change to optional host uvicorn on port 8000 (that path is not Compose); no rewrite of historical `docs/steps/step*.md`, `docs/issue_solve.md`, or `docs/blueprint_frontend.md`; no edit of `docs/FE_guide.md` (it still says Compose is on `:8000` — leftover for a follow-up); no frontend `.env` or CORS changes. Stub list (evaluation HTTP, `src/auth/dependencies.py`) stays as written. `AGENT.md` unchanged: no new packages, endpoints, or env vars.
