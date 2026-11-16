## ADDED Requirements

### Requirement: Test job runs architecture guardrails explicitly
The Phase A `test` job in `.github/workflows/ci.yml` MUST run `pytest tests/architecture -v` on every push and pull request to `main`, in addition to the existing full `pytest tests/ -v` invocation (or an equivalent ordering that still executes the architecture suite). The architecture step MUST use the same installed dependencies and MUST NOT require live Qdrant, Redis, or LLM provider credentials.

#### Scenario: Architecture step runs on PR
- **WHEN** a pull request targets `main` and CI starts
- **THEN** the workflow executes `pytest tests/architecture -v` and fails the job if that command exits non-zero

#### Scenario: Architecture step needs no provider secrets
- **WHEN** the architecture pytest step runs with empty or unset Langfuse and optional LLM secrets
- **THEN** the step still completes using only static AST/grep checks against the checkout
