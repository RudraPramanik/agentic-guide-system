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

### Requirement: Committed production env template uses Settings field names
The project SHALL provide `.env.production.example` (committed, no secrets) listing every production env var required for first boot with names matching `src/config.py` Settings. The template MUST document: `PLACES_EMBEDDING_BACKEND=hosted`, `PLACES_EMBEDDING_MODEL`, `PLACES_EMBEDDING_DIM=768`, `REDIS_URL` as `redis://` or `rediss://` (not HTTPS REST), `DATABASE_URL` as `postgresql+asyncpg://`, hosted `QDRANT_URL`, production OAuth redirect HTTPS path, and `CORS_ALLOWED_ORIGINS` without trailing slashes on origins.

#### Scenario: Operator copies template to server
- **WHEN** an operator copies `.env.production.example` to `.env.production` on the VPS and fills secrets
- **THEN** no ignored env aliases (e.g. `EMBEDDING_MODEL`, `UPSTASH_REDIS_REST_TOKEN`) are required for the app to boot

### Requirement: Blueprint references ops script ordering
`docs/steps/blueprint_production.md` MUST document first-deploy order: copy `.env.production` → `ops/migrate.sh` → optional Qdrant reindex → `ops/deploy.sh` → `ops/health.sh` → planner SSE smoke. It MUST state that `.env` (local) and `.env.production` (VPS) are separate files.

#### Scenario: First deploy sequence is explicit
- **WHEN** an operator follows the updated blueprint
- **THEN** they run migration before `compose up` and health smoke after deploy

### Requirement: VPS operator notes link blueprint and ops
`docs/vps.md` MUST summarize VPS baseline steps already completed and point to `docs/steps/blueprint_production.md` and `ops/` for application hosting (without embedding live secrets).

#### Scenario: Agent reads vps.md for deploy context
- **WHEN** a developer or Cursor agent opens `docs/vps.md`
- **THEN** they see next application-hosting steps and links to ops scripts
