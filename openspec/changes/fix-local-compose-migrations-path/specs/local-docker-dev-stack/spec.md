## ADDED Requirements

### Requirement: Local migrate-then-serve uses the Alembic scripts directory named in alembic.ini
The local development API image and Compose `api` service MUST provide Alembic with the scripts directory named by `alembic.ini` `script_location` (`migrations/`). Compose-only `alembic upgrade head` before uvicorn MUST find that directory inside the container. The production Dockerfile MUST remain the source of truth for VPS packaging and MUST NOT be changed by this requirement. Application lifespan MUST still not invoke Alembic.

#### Scenario: Local API becomes healthy after compose up
- **WHEN** a developer runs the documented local Compose up (rebuild as needed) from the API repo with a valid `.env` and existing PostGIS volume
- **THEN** `alembic upgrade head` MUST complete without a missing scripts-directory failure, the API process MUST bind host `:8000`, and `GET /api/v1/health` MUST succeed after startup

#### Scenario: Sibling catalog calls reach the API
- **WHEN** the local API is healthy and the sibling frontend uses `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **THEN** browser requests to `GET /api/v1/places` and `GET /api/v1/destinations/search` MUST not fail with connection refused because nothing is listening on `:8000`

#### Scenario: Production image contract unchanged
- **WHEN** an operator builds or deploys from the production Dockerfile
- **THEN** that file still copies `migrations/` as it does today, and VPS migrate-as-a-separate-step remains unchanged

### Requirement: Local operator CORS example keeps the sibling frontend origin
Local operator documentation and `.env.example` MUST state that `CORS_ALLOWED_ORIGINS` for laptop Compose MUST include the origin the developer actually opens (at least `http://localhost:3000` when the sibling Next app is on that origin). They MUST warn that copying a production-only origin list (for example a Vercel host alone) into local `.env` blocks credentialed browser calls. Gitignored `.env` MUST NOT be committed. This requirement MUST NOT change production CORS env or VPS allowlists.

#### Scenario: Example env lists localhost for local Next
- **WHEN** a developer copies `.env.example` to local `.env` for Compose
- **THEN** the documented `CORS_ALLOWED_ORIGINS` example MUST include `http://localhost:3000` (JSON list, never `*` with credentials)

#### Scenario: Docs warn against production-only CORS locally
- **WHEN** an operator reads the local boot / connection-refused issue notes
- **THEN** they MUST be told that a Vercel-only `CORS_ALLOWED_ORIGINS` in local `.env` will block `Origin: http://localhost:3000` even after the API is healthy
