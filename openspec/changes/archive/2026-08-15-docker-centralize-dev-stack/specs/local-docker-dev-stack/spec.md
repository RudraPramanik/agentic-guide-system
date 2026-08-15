## Purpose

Gives developers a single Compose command that starts the full local Wandr backend — PostGIS, Qdrant, Redis, and the FastAPI/uvicorn API with live reload — while keeping host pytest and scripts working against published ports.

## ADDED Requirements

### Requirement: Single command starts the local backend stack
Root `docker-compose.yml` MUST define local development services for PostGIS, Qdrant, Redis, and the Wandr API (uvicorn). A developer MUST be able to start the API plus its local data plane with one Compose invocation (`docker compose up --build` or equivalent). The root compose file MUST remain development-only and MUST NOT be used as the production data plane.

#### Scenario: One command brings API and data plane up
- **WHEN** a developer runs the documented single Compose command from a clean checkout with a valid `.env`
- **THEN** PostGIS, Qdrant, Redis, and the API process become reachable, and `GET /api/v1/health` on the published API port succeeds after startup

#### Scenario: Root compose is not production
- **WHEN** an operator follows production deploy docs
- **THEN** they are directed to hosted data stores and `docker-compose.prod.yml` (API + TLS proxy), not root `docker-compose.yml`

### Requirement: API container runs uvicorn with reload on published port 8000
The local API service MUST run uvicorn for `src.main:app` bound to `0.0.0.0:8000` with reload enabled for source changes. Host port **8000** MUST be published so browsers and the sibling frontend keep using `http://localhost:8000`. The API MUST wait until Postgres is healthy before serving.

#### Scenario: Docs and health on localhost:8000
- **WHEN** the local stack is up
- **THEN** `http://localhost:8000/docs` and `http://localhost:8000/api/v1/health` are reachable from the host

#### Scenario: Source change reloads without rebuild
- **WHEN** a Python file under the bind-mounted application source changes while the API service is running
- **THEN** uvicorn reloads the process without requiring a Compose rebuild

### Requirement: Container env uses Docker DNS; host env keeps published ports
The API service MUST override `DATABASE_URL`, `QDRANT_URL`, and `REDIS_URL` to in-compose hostnames and internal ports (`postgres:5432`, `qdrant:6333`, Redis internal 6379). Host `.env` values targeting `localhost:5433` / `localhost:6335` / empty `REDIS_URL` MUST remain valid for host pytest, scripts, and optional host uvicorn. Application code MUST continue to read env only through `get_settings()`.

Published host ports MUST stay: Postgres **5433**, Qdrant **6335** (HTTP) / **6336** (gRPC). Redis, if published, MUST use a non-default host port to avoid clashing with a host Redis on 6379.

#### Scenario: API container talks to compose services
- **WHEN** the API process starts inside Compose
- **THEN** it connects to Postgres, Qdrant, and Redis via Docker service DNS, not `localhost` published ports

#### Scenario: Host pytest still uses localhost published ports
- **WHEN** a developer runs `python -m pytest tests/ -v` on the host with existing `.env` (`DATABASE_URL` on `:5433`, `QDRANT_URL` on `:6335`, empty `REDIS_URL`)
- **THEN** tests continue to reach PostGIS and Qdrant on those published ports and keep in-memory cache/rate-limit backends

### Requirement: Dev image includes full local dependencies; prod image stays slim
The local API image MUST install the full development dependency set (`requirements.txt`), including local MiniLM support. The existing production Dockerfile MUST continue to use `requirements-prod.txt` and MUST NOT require `sentence-transformers` or `torch` when hosted embeddings are selected.

#### Scenario: Local stack can use MiniLM backend
- **WHEN** `PLACES_EMBEDDING_BACKEND=local` in the API service environment
- **THEN** the local API image has the packages needed to load MiniLM without switching to the production Dockerfile

#### Scenario: Production image contract unchanged
- **WHEN** the production image is built from the production Dockerfile
- **THEN** it still starts with hosted embeddings and a single uvicorn worker, with no PostGIS/Qdrant/Redis in `docker-compose.prod.yml`

### Requirement: Dev migrate-then-serve is Compose-only
The local API service MAY run `alembic upgrade head` before uvicorn as a Compose entrypoint/command. Application lifespan MUST NOT gain auto-migrate. Production MUST continue to migrate as a separate operator step.

#### Scenario: Local first boot applies migrations then serves
- **WHEN** the API service starts against an empty local PostGIS volume
- **THEN** migrations apply and the API becomes healthy without a separate host alembic command

#### Scenario: Lifespan still does not migrate
- **WHEN** the FastAPI app lifespan runs (container or host)
- **THEN** it does not invoke Alembic; it still pings DB, ensures Qdrant collection, and loads embeddings per existing contract
