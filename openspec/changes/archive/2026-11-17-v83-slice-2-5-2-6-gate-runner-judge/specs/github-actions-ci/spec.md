## ADDED Requirements

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
