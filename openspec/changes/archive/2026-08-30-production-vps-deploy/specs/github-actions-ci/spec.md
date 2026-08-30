## ADDED Requirements

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
