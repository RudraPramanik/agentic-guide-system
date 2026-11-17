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

### Requirement: Test job runs architecture guardrails explicitly
The Phase A `test` job in `.github/workflows/ci.yml` MUST run `pytest tests/architecture -v` on every push and pull request to `main`, in addition to the existing full `pytest tests/ -v` invocation (or an equivalent ordering that still executes the architecture suite). The architecture step MUST use the same installed dependencies and MUST NOT require live Qdrant, Redis, or LLM provider credentials.

#### Scenario: Architecture step runs on PR
- **WHEN** a pull request targets `main` and CI starts
- **THEN** the workflow executes `pytest tests/architecture -v` and fails the job if that command exits non-zero

#### Scenario: Architecture step needs no provider secrets
- **WHEN** the architecture pytest step runs with empty or unset Langfuse and optional LLM secrets
- **THEN** the step still completes using only static AST/grep checks against the checkout

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

### Requirement: PR and main run a replay eval-gate job
The CI configuration MUST include an eval-gate job that runs on `push` to `main` and on `pull_request` targeting `main`. That job MUST invoke `python scripts/run_evals.py --destination darjeeling --replay` (or an equivalent documented command that forces gateway replay for Darjeeling). The job MUST fail when the command exits non-zero. The job MUST NOT require a live LLM API key. The existing pytest and docker-build jobs MUST remain. The eval-gate job MAY provision the services required for `PlannerService.generate` under replay (including Qdrant when the runner still calls generate). It MUST NOT deploy, push images, or SSH to production.

#### Scenario: PR runs replay eval-gate
- **WHEN** a pull request targets `main` and CI starts
- **THEN** the workflow runs the Darjeeling suite with `--replay` and fails the job if that command exits non-zero

#### Scenario: Eval-gate needs no live LLM key
- **WHEN** the eval-gate job runs with an empty LLM API key and committed replay fixtures
- **THEN** the job still completes using replay and does not call a provider

#### Scenario: Eval-gate does not deploy
- **WHEN** the eval-gate job finishes green
- **THEN** no deploy, migrate-prod, or registry-publish step has run from that job

### Requirement: Nightly live eval does not block PRs
The repository MUST provide a scheduled (nightly) workflow or job that runs the golden suite without `--replay` when secrets allow a live model. A live-mode failure MUST NOT fail pull-request CI. The nightly job MUST surface the failure in job logs so a blocking ticket can be opened. When live secrets are absent, the nightly job MUST skip the live generate path with a clear skip reason rather than inventing results.

#### Scenario: Nightly schedule exists
- **WHEN** the scheduled live eval workflow is inspected
- **THEN** it defines a cron (or equivalent schedule) distinct from the PR-triggered eval-gate job

#### Scenario: PR CI ignores nightly live flakiness
- **WHEN** the nightly live job fails and a pull request is opened the same day
- **THEN** the PR eval-gate job still uses `--replay` and does not require the nightly live result to be green
