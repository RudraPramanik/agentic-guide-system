## Purpose

Offline golden-dataset evaluation harness: property-based itinerary cases replayed through the real generation pipeline, scored by deterministic pure-Python scorers, with run reports and baseline diffing for regression gating.

## Requirements

### Requirement: Golden case schema is property-based
Golden cases SHALL be versioned JSON files grouped per destination, asserting *properties* of a generated itinerary (constraint satisfaction, must-include places, validation pass, readiness/fallback/tool-call bounds) — never exact output strings or place orderings. Each case MUST carry a stable id, destination, raw input, and at least one assertion.

#### Scenario: Case file validates against schema
- **WHEN** the runner loads golden cases for a destination
- **THEN** every case has an id, destination, input, and ≥1 assertion; malformed cases fail fast with the offending file named

### Requirement: Deterministic scorers are pure functions
Scorers SHALL be pure Python functions (no LLM, no network, no DB I/O) that take a generation result plus a case and return pass/fail with a reason. Route feasibility scoring MUST reuse the existing trip validator. Scoring MUST NOT mutate inputs.

#### Scenario: Feasibility scorer reuses trip validator
- **WHEN** a case asserts `validation_passed`
- **THEN** the scorer's verdict matches what the existing trip validator reports for the generated itinerary

#### Scenario: Scorers are deterministic
- **WHEN** the same result is scored twice
- **THEN** both runs return identical verdicts and reasons

### Requirement: Runner replays through the production pipeline
The runner SHALL execute each golden case through the same planner service entry point used in production, with routing injected via the test fake-routing pattern, and SHALL NOT require live external services beyond those already required by the dev stack (DB, Qdrant, optional LLM). Each run SHALL produce a machine-readable report (per-case verdicts, scores, timings, git SHA, timestamp) under `evals/runs/`.

#### Scenario: Full suite run produces report
- **WHEN** the runner executes all cases for a destination
- **THEN** a single JSON report exists listing every case id with verdict, individual assertion results, and aggregate pass rate

#### Scenario: LLM-unavailable mode still scores deterministic assertions
- **WHEN** no LLM key is configured and cases are replayed from recorded states or fallback paths
- **THEN** deterministic assertions (constraints, validator, fallback flags) are still evaluated and reported

### Requirement: Baseline diff gates regressions
The runner SHALL compare a new run against a designated baseline report and exit non-zero when any previously-passing case regresses to fail. A `--update-baseline` mode SHALL freeze the current run as the new baseline explicitly.

#### Scenario: Regression exits non-zero
- **WHEN** a case passed in the baseline but fails in the new run
- **THEN** the runner prints the diff for that case and exits non-zero

#### Scenario: All-pass run exits zero
- **WHEN** every case passes identically to baseline
- **THEN** the runner exits zero

#### Scenario: Baseline update is explicit
- **WHEN** the runner is invoked with the update-baseline flag
- **THEN** the current run replaces the stored baseline and the command exits zero
