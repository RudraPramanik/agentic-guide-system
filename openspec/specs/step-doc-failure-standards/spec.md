## Purpose

Documentation standards requiring failure boundaries and verifiable failure proofs in all build step prompts.

## Requirements

### Requirement: Canonical failure standards document exists

The project SHALL maintain `docs/steps/FAILURE_STANDARDS.md` defining mandatory failure sections for all step prompt files, minimum failure-proof counts by step category, and links to `docs/blueprint_final.md` Resilience Contracts and Failure Boundary Summary tables.

#### Scenario: Agent reads standards before authoring step doc

- **WHEN** a developer or agent starts writing `docs/steps/stepN.md`
- **THEN** `FAILURE_STANDARDS.md` is discoverable from Prompt conventions in existing step files and from `docs/spec.md`

### Requirement: Every step prompt includes failure boundary block

Each step prompt block in `docs/steps/step*.md` SHALL include a `─── FAILURE BOUNDARY ───` section citing a blueprint row, naming the on-failure behavior, and listing at least one "Must NOT" constraint.

#### Scenario: P2 gateway step documents OSRM fallback

- **WHEN** step 2.5 (OSRM) prompt is written
- **THEN** its FAILURE BOUNDARY section cites OSRM resilience contract and states haversine fallback — not HTTP 500

### Requirement: Every step prompt includes failure validation

Each step prompt block SHALL include a `✅ Failure path:` validation line with a verifiable command or test and expected outcome (status code, fallback flag, empty list, etc.).

#### Scenario: Dual validation gate

- **WHEN** an agent completes a step
- **THEN** both happy-path and failure-path ✅ checks are documented and must pass before advancing

### Requirement: Minimum failure proofs by category

Step docs SHALL meet minimum failure-proof counts: external gateway ≥2, HTTP API ≥1, middleware ≥1, agent/tool ≥2, batch script ≥1, pure Python validator ≥1 bad-input case.

#### Scenario: Under-specified geo step rejected in review

- **WHEN** a geo gateway step doc has only a happy-path ✅ check
- **THEN** it does not meet failure standards and must be revised before implementation

### Requirement: OpenSpec changes include failure scenarios

OpenSpec delta specs for capabilities with external I/O SHALL include at least one `#### Scenario:` describing failure/fallback behavior aligned with the blueprint.

#### Scenario: Geo capability spec

- **WHEN** an OpenSpec change adds a geocoder capability
- **THEN** its spec includes a scenario for network failure returning `None` or typed 404 — not unhandled exception

### Requirement: Playbook references failure standards

`docs/spec.md` SHALL include a subsection linking step authoring → failure standards → OpenSpec failure scenarios → P6 ship checklist chaos tests.

#### Scenario: Developer follows playbook

- **WHEN** a developer reads `docs/spec.md` Phase 2 planning section
- **THEN** they find explicit guidance to add failure proofs to tasks.md and step prompts
