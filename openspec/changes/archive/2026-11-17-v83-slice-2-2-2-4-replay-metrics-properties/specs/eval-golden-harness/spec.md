## ADDED Requirements

### Requirement: Replay runs the golden suite twice identically
`scripts/run_evals.py --replay` MUST force gateway replay for that process even when `LLM_REPLAY_MODE` is `off`. It MUST NOT read or write process environment variables. It MUST NOT call a provider. Two consecutive `--replay` runs of the same destination MUST produce the same per-case verdicts and the same reasons. A missing fixture MUST make that run exit non-zero and MUST print `replay_miss`. `--replay` MUST NOT change baseline files, MUST NOT change `--update-baseline` or `--fixtures-only`, and MUST NOT change schema validation or how a case passes or fails.

#### Scenario: Two replay runs match
- **WHEN** the Darjeeling suite is run with `--replay` twice and every gateway call has a fixture
- **THEN** the per-case verdicts and reasons are identical and the provider is not called

#### Scenario: Missing fixture fails the run
- **WHEN** `--replay` reaches a gateway call with no fixture
- **THEN** the process exits non-zero and the output contains `replay_miss`

#### Scenario: Replay leaves the baseline untouched
- **WHEN** `--replay` finishes
- **THEN** the stored baseline files are unchanged
