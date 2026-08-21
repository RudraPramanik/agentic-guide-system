## ADDED Requirements

### Requirement: Host Compose .env is visible inside the API container
The local Compose `api` service MUST bind-mount the host project `.env` at `/app/.env` (read-only) so Settings `env_file=".env"` loads the same operator file after container recreate. Compose MUST still override `DATABASE_URL`, `QDRANT_URL`, and `REDIS_URL` to in-compose DNS (`postgres:5432`, `qdrant:6333`, Redis internal 6379). Application code MUST continue to read env only through `get_settings()`. The file MUST remain gitignored and MUST NOT be baked into the image (`.dockerignore` keeps `.env` out of the build context).

#### Scenario: Recreate still loads host .env
- **WHEN** an operator has a valid host `.env` and runs `docker compose down` then `docker compose up` from the API repo
- **THEN** the API process MUST start using that same `.env` without the operator re-pasting keys, and `GET /api/v1/health` on host `:8000` MUST succeed after startup

#### Scenario: Container does not use host localhost data-plane ports
- **WHEN** the API process runs inside Compose and host `.env` still has `DATABASE_URL` on `localhost:5433` (or Qdrant `localhost:6335`)
- **THEN** the API MUST connect to Postgres, Qdrant, and Redis via Docker service DNS, not those published host ports

### Requirement: Compose down then up restores catalog on :8000
`docker compose down` MAY unbind host `:8000`. A subsequent documented `up` MUST bring PostGIS, Qdrant, Redis, and the API back. Operator docs MUST state that sibling FE `ERR_CONNECTION_REFUSED` during the down window is expected, and that after `up` + healthy `wandr_api`, destinations search MUST connect without changing frontend `NEXT_PUBLIC_API_URL`.

#### Scenario: Down then up restores destinations search
- **WHEN** the stack is taken down with `docker compose down` (volumes kept) and started again with `docker compose up`
- **THEN** after the API is healthy, `GET /api/v1/destinations/search?q=darjeeling` on host `:8000` MUST return HTTP 200 (not connection refused)
