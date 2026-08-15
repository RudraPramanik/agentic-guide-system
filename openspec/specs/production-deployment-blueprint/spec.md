## Purpose

Operator-facing production deploy SOP for MVP: API on a VPS with hosted PostGIS, Qdrant, Redis, chat LLM, and place embeddings.

## Requirements

### Requirement: Production blueprint documents hosted VPS topology
The project SHALL provide `docs/steps/blueprint_production.md` as the operator SOP for MVP production: API container on a VPS; Postgres/PostGIS, Qdrant, Redis, chat LLM, and place embeddings hosted; no prod docker-compose for data services.

The blueprint MUST include ordered steps for account presetup, env population, image build/run, reverse proxy/TLS, SSE non-buffering for planner generate, `alembic upgrade head`, Qdrant collection dim cutover, reindex, and smoke checks.

#### Scenario: Operator can follow deploy without reading OpenSpec
- **WHEN** an operator opens `docs/steps/blueprint_production.md`
- **THEN** they can complete presetup through first successful `/api/v1/health` and one planner SSE without needing worker/queue or self-hosted DB instructions

### Requirement: Env and API checklist is explicit
The production blueprint MUST list every external account/API to provision and every application env var required for first boot (database, Qdrant, Redis, LLM, Gemini embeddings, Google OAuth, CORS, secrets, geo user-agent), including which values are prod-only vs optional.

#### Scenario: Checklist covers embeddings and OAuth redirect
- **WHEN** an operator follows the checklist section
- **THEN** they see `PLACES_EMBEDDING_BACKEND`/`MODEL`/`DIM`, Gemini API key handling, and `GOOGLE_REDIRECT_URI` pointing at the HTTPS API callback path

### Requirement: Local compose remains development-only
The root `docker-compose.yml` (local PostGIS, Qdrant, Redis, and API) MUST remain documented as local development infra only and MUST NOT be prescribed as the production data plane.

#### Scenario: Blueprint separates dev and prod compose
- **WHEN** the blueprint describes containers on the VPS
- **THEN** it lists at most API + TLS proxy (optional compose), and directs data stores to hosted URLs
