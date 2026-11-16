## Purpose

Records the four Slice 0 architecture decisions and keeps every unmeasured `[SET IN S0]` release target as a placeholder so later slices cannot treat a guess as the baseline.

## ADDED Requirements

### Requirement: ADR-001 through ADR-004 are accepted records
The repository SHALL contain four decision records under `docs/v8.2/adr/` for modular monolith, `/api/v1` additive compatibility, bounded execution, and deterministic validator versus LLM judge. Each record MUST include context, decision, alternatives, consequences, migration and rollback, and status `accepted`. The records MUST NOT add a module, flag, endpoint, or judge that the checkout does not already have.

#### Scenario: Four records exist
- **WHEN** subslice 0.4 is complete
- **THEN** all four records exist, each status is accepted, and none of them creates `planner/runs/`, `location_intelligence/`, or an in-path judge

#### Scenario: Bounded execution keeps the existing ceiling
- **WHEN** the bounded-execution record states the generate latency ceiling
- **THEN** that ceiling is the existing 45 second planner timeout, and the record does not raise it

#### Scenario: Judge cannot override a critical finding
- **WHEN** the validator-versus-judge record states responsibilities
- **THEN** a deterministic critical finding is never overridden by a judge, and an uncalibrated judge does not gate or repair the request path

### Requirement: Unmeasured targets stay placeholders
`docs/v8.2/s0_targets.md` MUST restate the §4 target table. Generate p50, LLM calls per trip, tokens per trip, and cost per trip MUST remain `[SET IN S0]` when `docs/v8.2/baseline_metrics.md` marks them unmeasured. Generate p95 MUST be recorded as not measured, and the "already over 45 seconds" stop MUST be recorded as not evaluable. The blueprint source file MUST NOT be edited to clear its placeholders.

#### Scenario: No invented multiplier base
- **WHEN** the baseline doc marks p50, LLM calls, tokens, or cost unmeasured
- **THEN** the targets doc leaves that cell as `[SET IN S0]` and does not write a number

#### Scenario: p95 stop is not guessed
- **WHEN** the baseline doc has no p95 measurement
- **THEN** the targets doc says the p95 stop cannot be evaluated and does not claim the ceiling was met or missed

#### Scenario: Slice 3 still waits
- **WHEN** a later slice looks for filled `[SET IN S0]` values
- **THEN** the targets doc states that Slice 3 must not start on these four gates until a measured baseline exists
