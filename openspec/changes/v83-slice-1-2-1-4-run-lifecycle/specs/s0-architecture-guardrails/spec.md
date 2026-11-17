## ADDED Requirements

### Requirement: Run status is written only by the lifecycle service
The architecture suite MUST fail when a Python file other than `src/planner/runs/service.py` assigns a planner run's status. The model field and its default are not a violation. Other modules MAY call the lifecycle service to request a transition. `tests/architecture/VIOLATIONS.md` MUST NOT list G15 as deferred.

#### Scenario: Router assigning status fails the suite
- **WHEN** a module outside `src/planner/runs/service.py` assigns a planner run status
- **THEN** the architecture suite fails and names that module

#### Scenario: G15 is no longer deferred
- **WHEN** the violations document is read
- **THEN** the deferred-rule section does not list G15

## MODIFIED Requirements

### Requirement: Known violations are ticketed and allowlisted
When a rule already fails on the current checkout, the suite MUST record each offending path in `tests/architecture/VIOLATIONS.md` with the rule id and a short ticket note. Tests MUST treat that list as an allowlist: paths on the list do not fail the suite, and any new path that breaks the same rule MUST fail. Application source under `src/` MUST NOT be edited solely to clear an allowlisted violation during this subslice.

#### Scenario: Pre-existing env write stays allowlisted
- **WHEN** `src/core/observability/tracing.py` writes Langfuse settings into `os.environ` and is listed under G3 in the violations file
- **THEN** the architecture suite still exits 0

#### Scenario: New env access outside config fails
- **WHEN** another module under `src/` uses `os.environ` or `os.getenv` and is not on the G3 allowlist
- **THEN** the architecture suite fails and names that module

#### Scenario: Deferred rules are documented, not invented
- **WHEN** a §10 rule cannot be enforced yet because its module is absent or is owned by another suite (snapshots, golden replay)
- **THEN** the violations or suite docs record the deferral, the suite does not invent that module, and G15 is not in the deferred list
