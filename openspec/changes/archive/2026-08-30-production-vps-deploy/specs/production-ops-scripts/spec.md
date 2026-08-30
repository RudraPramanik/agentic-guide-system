## Purpose

Repeatable shell operators for VPS production deploy, migration, health checks, and rollback — shared by human operators and CI/CD SSH steps.

## ADDED Requirements

### Requirement: Ops scripts exist for production lifecycle
The repository SHALL provide executable scripts under `ops/` for: `migrate.sh`, `deploy.sh`, `health.sh`, `status.sh`, `logs.sh`, `rollback.sh`, and `backup.sh`. Each script MUST use `docker-compose.prod.yml` (API + Caddy only) and MUST NOT start local PostGIS, Qdrant, or Redis containers.

#### Scenario: Operator lists available ops commands
- **WHEN** an operator lists `ops/`
- **THEN** all seven lifecycle scripts are present and executable

### Requirement: Migrate runs Alembic against hosted DATABASE_URL
`ops/migrate.sh` MUST run `alembic upgrade head` in a one-off container using the production API image and `.env.production` (or path override via env). It MUST exit non-zero on migration failure and MUST NOT start the long-running API service.

#### Scenario: Successful migration
- **WHEN** `ops/migrate.sh` runs with valid `.env.production` and pending migrations
- **THEN** Alembic applies migrations and exits 0

#### Scenario: Failed migration aborts
- **WHEN** `ops/migrate.sh` runs and Alembic fails
- **THEN** the script exits non-zero without invoking `compose up`

### Requirement: Deploy pulls image and restarts compose stack
`ops/deploy.sh` MUST accept an optional image tag or digest (default: local `wandr-api:prod` or registry image set via env). It MUST run `docker compose -f docker-compose.prod.yml pull` (when registry image configured) and `up -d` for the API and Caddy services. It MUST NOT run `docker build` on the VPS by default.

#### Scenario: Deploy restarts API and proxy
- **WHEN** `ops/deploy.sh` runs with valid env and image available
- **THEN** `docker compose -f docker-compose.prod.yml` reports API and Caddy running

### Requirement: Health script smoke-checks production API
`ops/health.sh` MUST call `GET /api/v1/health` against the configured public API base URL (from env or argument) and exit 0 only on HTTP 200. It MAY optionally check TLS reachability.

#### Scenario: Healthy API passes smoke
- **WHEN** the API is up behind Caddy and health returns 200
- **THEN** `ops/health.sh` exits 0

#### Scenario: Down API fails smoke
- **WHEN** the API is unreachable or health is non-200
- **THEN** `ops/health.sh` exits non-zero

### Requirement: Rollback redeploys previous image tag
`ops/rollback.sh` MUST redeploy a previously recorded image tag (from a deploy stamp file or explicit argument) using the same compose file, without running Alembic downgrade unless explicitly documented as out of scope.

#### Scenario: Rollback to prior tag
- **WHEN** `ops/rollback.sh <previous-tag>` runs and the image exists locally or in registry
- **THEN** compose restarts API with the prior image and `health.sh` can be run afterward

### Requirement: Status and logs wrap compose observability
`ops/status.sh` MUST print compose service status for the prod stack. `ops/logs.sh` MUST tail API and/or Caddy logs via `docker compose logs` with a sensible default follow mode.

#### Scenario: Operator inspects running stack
- **WHEN** `ops/status.sh` runs
- **THEN** output shows whether `api` and `caddy` containers are up

### Requirement: Backup documents hosted-data scope
`ops/backup.sh` MUST document or invoke backup steps appropriate for hosted data plane (e.g., remind operator to use provider backups for PostGIS/Qdrant) and MUST NOT dump secrets into the repository.

#### Scenario: Backup does not commit secrets
- **WHEN** `ops/backup.sh` runs
- **THEN** no `.env.production` contents are written into tracked files
