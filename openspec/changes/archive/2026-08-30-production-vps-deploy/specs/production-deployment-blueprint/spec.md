## ADDED Requirements

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
