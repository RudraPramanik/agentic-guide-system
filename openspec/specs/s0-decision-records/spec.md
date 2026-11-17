## Purpose

Records the four Slice 0 architecture decisions and keeps every unmeasured `[SET IN S0]` release target as a placeholder so later slices cannot treat a guess as the baseline.

## Requirements

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

### Requirement: ADR-006 records run tracking and idempotency scope
The repository SHALL contain an accepted decision record at `docs/v8.2/adr/006-run-tracking-idempotency.md` with context, decision, alternatives, consequences, migration and rollback, and status `accepted`. The record MUST state that the idempotency key is not the preference-cache key, that the preference-cache key is unchanged, that this slice adds no checkpoint, resume, lease, or worker, and that it adds no cancel route. Disconnect remains the way an in-flight generate stops. The record MUST state that `RUN_TRACKING_ENABLED` defaults to false.

#### Scenario: Record exists and is accepted
- **WHEN** subslice 1.2–1.4 is complete
- **THEN** `docs/v8.2/adr/006-run-tracking-idempotency.md` exists and its status is `accepted`

#### Scenario: Cache key stays separate
- **WHEN** the record states how a repeated submit is identified
- **THEN** it says the idempotency key is not the preference-cache key and the cache key is unchanged

#### Scenario: Cancel route and resume stay out
- **WHEN** the record states what this slice refuses
- **THEN** it says there is no cancel route, no checkpoint, and no resume, and that client disconnect still stops the in-flight generate

#### Scenario: Rollback is the flag
- **WHEN** the record states rollback
- **THEN** it says `RUN_TRACKING_ENABLED` defaults to false and turning it off restores generate without run writes

### Requirement: ADR-007 records evaluation gates and tolerances
The repository SHALL contain an accepted decision record at `docs/v8.2/adr/007-evaluation-gates.md` with context, decision, alternatives, consequences, migration and rollback, and status `accepted`. The record MUST state that deterministic case pass/fail for non-quarantined cases gates releases, that tolerance-banded metrics gate only when S0 measured variance exists, that CI PRs use replay while live runs are scheduled and do not block PRs on flakiness, that baselines change only via explicit `--update-baseline` in a reviewed PR, and that the offline judge informs and does not gate until §11.8 promotion. The record MUST state that expanding the golden set to §11.2 minimums (≥24 cases, ≥3 destinations) remains a Slice 2 exit checklist item outside rows 2.5 and 2.6 path cells.

#### Scenario: Record exists and is accepted
- **WHEN** subslices 2.5 and 2.6 are complete
- **THEN** `docs/v8.2/adr/007-evaluation-gates.md` exists and its status is `accepted`

#### Scenario: Unmeasured bands cannot gate
- **WHEN** the record states how tolerance bands apply
- **THEN** it says a metric without measured baseline variance cannot hard-fail the gate

#### Scenario: Judge stays inform-only here
- **WHEN** the record states the judge role for this slice
- **THEN** it says the offline judge does not gate and does not run on the request path

#### Scenario: Case expansion stays a checklist item
- **WHEN** the record states golden-set size
- **THEN** it says ≥24 cases across ≥3 destinations is still required for Slice 2 exit and is not claimed done by shipping the gate runner alone
