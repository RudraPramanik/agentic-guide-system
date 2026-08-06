## Purpose

Production Docker packaging for the Wandr API on a VPS: slim image without local embedding ML, optional API+proxy compose, SSE-safe reverse proxy.

## Requirements

### Requirement: Production Dockerfile packages the API without local embedding ML
The project SHALL provide a production Dockerfile that builds and runs the Wandr FastAPI API. The production runtime image MUST NOT require `sentence-transformers` or `torch` to start when `PLACES_EMBEDDING_BACKEND=hosted`.

Default process MUST be a single uvicorn worker (`--workers 1`) binding `0.0.0.0` for reverse-proxy use on small VPS hosts.

#### Scenario: Hosted embeddings image starts without MiniLM
- **WHEN** the production image is built and run with hosted embedding settings and valid env
- **THEN** the process reaches lifespan completion without downloading or loading a local SentenceTransformer model

#### Scenario: Single worker is the documented default
- **WHEN** an operator uses the documented production CMD/entrypoint
- **THEN** uvicorn runs with exactly one worker

### Requirement: Optional VPS compose is API and proxy only
If a production compose file is provided, it MUST include only the API service and an optional TLS reverse proxy. It MUST NOT start Postgres, Qdrant, or Redis containers for production.

#### Scenario: Prod compose has no data services
- **WHEN** production compose is inspected
- **THEN** there is no PostGIS/Qdrant/Redis service definition intended for prod use

### Requirement: Reverse proxy preserves planner SSE
Production proxy configuration (documented example for Caddy or nginx) MUST terminate TLS and MUST disable response buffering for `POST /api/v1/planner/generate` so SSE events flush to the client.

#### Scenario: Planner path is non-buffered
- **WHEN** proxy config from the blueprint/examples is applied
- **THEN** the planner generate location has buffering disabled (or equivalent Caddy flush behavior)
