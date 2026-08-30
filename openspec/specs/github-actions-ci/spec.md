## Purpose

GitHub Actions CI/CD for the Wandr backend: Phase A runs pytest and production Docker image build on every push and pull request to main; Phase B-lite (optional) publishes to GHCR and deploys via `ops/*.sh` over SSH (`workflow_dispatch`).

## Requirements

### Requirement: CI workflow runs on main push and pull requests
The repository SHALL provide a GitHub Actions workflow at `.github/workflows/ci.yml` that runs on `push` to `main` and on `pull_request` targeting `main`.

#### Scenario: Push to main triggers CI
- **WHEN** a commit is pushed to `main`
- **THEN** the CI workflow starts without requiring manual dispatch

#### Scenario: PR to main triggers CI
- **WHEN** a pull request targets `main`
- **THEN** the CI workflow starts for that PR

### Requirement: Test job runs full pytest suite against PostGIS test DB
The CI workflow SHALL include a `test` job that installs Python matching the production Dockerfile major.minor, installs dependencies from `requirements.txt`, provisions a PostGIS-capable PostgreSQL service (or equivalent), sets `DATABASE_URL` so the suite can derive `wandr_test`, and runs `pytest tests/ -v`. The job MUST NOT require live Qdrant, Redis, or LLM provider credentials.

#### Scenario: Pytest green on a healthy PR
- **WHEN** the test job runs against a branch whose suite passes locally with the same deps
- **THEN** `pytest tests/ -v` exits 0

#### Scenario: No provider secrets required
- **WHEN** the test job runs with empty/unset Langfuse and optional LLM secrets
- **THEN** the suite still completes (tests mock external I/O)

### Requirement: Docker-build job builds production Dockerfile
The CI workflow SHALL include a `docker-build` job that runs `docker build -f Dockerfile .` and MUST NOT push images to any registry.

#### Scenario: Prod image builds
- **WHEN** the docker-build job runs with a valid Dockerfile and `requirements-prod.txt`
- **THEN** the image build exits 0 and no registry push occurs

### Requirement: Phase A CI has no deploy side effects
Phase A CI MUST NOT deploy to any environment, run Alembic against production, or publish artifacts beyond job logs.

#### Scenario: Green CI does not deploy
- **WHEN** CI completes successfully
- **THEN** no deploy, migrate-prod, or registry-publish step has run

### Requirement: Phase B-lite deploy workflow publishes production image
The repository SHALL provide a GitHub Actions workflow (e.g. `.github/workflows/deploy.yml`) that runs after Phase A CI gates on `main` (or via `workflow_dispatch`), builds the production Dockerfile, pushes to GHCR tagged with the git SHA, and MUST NOT use `latest` as the sole deploy tag.

#### Scenario: Main merge builds and pushes image
- **WHEN** deploy workflow runs on a green `main` commit
- **THEN** `ghcr.io/<owner>/wandr-api:<sha>` (or documented equivalent) exists in the registry

#### Scenario: Image tag is immutable per commit
- **WHEN** two commits deploy in sequence
- **THEN** each deploy uses a distinct SHA tag

### Requirement: Deploy job invokes ops scripts over SSH
The deploy workflow SHALL SSH to the production VPS, set the target image tag, run `ops/migrate.sh` (abort deploy on failure), then `ops/deploy.sh <sha>`, then `ops/health.sh`. Registry credentials and SSH keys MUST come from GitHub Secrets, not the repository.

#### Scenario: Migration failure blocks deploy
- **WHEN** `ops/migrate.sh` exits non-zero in the deploy job
- **THEN** `ops/deploy.sh` does not run and the workflow fails

#### Scenario: Health failure fails the workflow
- **WHEN** deploy completes but `ops/health.sh` exits non-zero
- **THEN** the workflow is marked failed (rollback may be manual via `ops/rollback.sh`)

### Requirement: Phase B-lite preserves Phase A non-deploy guarantees on PRs
Pull requests MUST continue to run only Phase A (`ci.yml` test + docker-build) without SSH deploy or registry push unless explicitly triggered by a separate manual workflow.

#### Scenario: PR does not deploy
- **WHEN** a pull request targets `main`
- **THEN** only `ci.yml` runs and no deploy workflow pushes to GHCR or SSHs to prod
