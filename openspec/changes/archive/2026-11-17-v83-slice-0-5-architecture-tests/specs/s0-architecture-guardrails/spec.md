## Purpose

Machine-enforced Slice 0 architecture guardrails: pytest under `tests/architecture/` blocks new import and purity violations while known existing breaches stay ticketed and allowlisted.

## ADDED Requirements

### Requirement: Import and purity rules are enforced by architecture tests
The repository MUST provide pytest modules under `tests/architecture/` that fail when any of the following appear outside their allowed locations: `litellm` / `groq` / `openai` imports outside `src/core/llm/client.py`; I/O or geo imports (`geo`, `httpx`, `sqlalchemy`, `qdrant_client`, `litellm`, `requests`, `redis`, or `src.geo`) inside `src/travel_engine/**`; `os.environ` or `os.getenv` outside `src/config.py`; concrete tool-implementation imports from `src/planner/graph/nodes/**`; repository imports from `*router.py` files. The suite MUST also fail when graph TypedDict state declares `AsyncSession` or `RoutingProvider` fields, when a documented feature flag defaults to a non-legacy on value, when a `ValidationFinding.code` is missing from the stable registry, or when `src/planner/service.py` or `src/travel_engine/**` import a lodging client or `src/geo/media/`.

#### Scenario: Clean tree passes architecture tests
- **WHEN** `pytest tests/architecture -v` runs against a tree whose only allowlisted breaches are listed in the violations file
- **THEN** the suite exits 0

#### Scenario: New litellm import outside the gateway fails
- **WHEN** a module other than `src/core/llm/client.py` gains an import of `litellm`, `groq`, or `openai`
- **THEN** the architecture suite fails and names that module

#### Scenario: travel_engine I/O import fails
- **WHEN** a file under `src/travel_engine/` imports a forbidden I/O or geo module
- **THEN** the architecture suite fails and names that file

#### Scenario: Router repository import fails
- **WHEN** a `*router.py` file imports a repository module or `BaseRepository`
- **THEN** the architecture suite fails and names that router

### Requirement: Known violations are ticketed and allowlisted
When a rule already fails on the current checkout, the suite MUST record each offending path in `tests/architecture/VIOLATIONS.md` with the rule id and a short ticket note. Tests MUST treat that list as an allowlist: paths on the list do not fail the suite, and any new path that breaks the same rule MUST fail. Application source under `src/` MUST NOT be edited solely to clear an allowlisted violation during this subslice.

#### Scenario: Pre-existing env write stays allowlisted
- **WHEN** `src/core/observability/tracing.py` writes Langfuse settings into `os.environ` and is listed under G3 in the violations file
- **THEN** the architecture suite still exits 0

#### Scenario: New env access outside config fails
- **WHEN** another module under `src/` uses `os.environ` or `os.getenv` and is not on the G3 allowlist
- **THEN** the architecture suite fails and names that module

#### Scenario: Deferred rules are documented, not invented
- **WHEN** a §10 rule cannot be enforced yet because its module is absent (for example run-status transitions) or is owned by another suite (snapshots, golden replay)
- **THEN** the violations or suite docs record the deferral and the suite does not invent that module
