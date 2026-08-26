## Purpose

Minimal GitHub Actions continuous integration for the Wandr backend: automated pytest and production Docker image build on every push and pull request to main, with no deploy or registry publish.

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
