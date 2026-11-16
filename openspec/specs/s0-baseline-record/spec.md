## Purpose

Freezes a repeatable Darjeeling golden-suite baseline from the existing fixtures-only runner, and labels every Slice 0 metric the runner cannot emit as unmeasured.

## Requirements

### Requirement: Fixtures-only runs are the Slice 0 baseline
The Slice 0 Darjeeling baseline MUST be produced by two invocations of the existing eval runner in fixtures-only mode. The two reports MUST agree on pass rate, and on each case id, passed flag, reasons, and mode. Timestamps and run filenames MUST be ignored in that comparison. The runner source MUST stay unchanged.

#### Scenario: Two fixtures-only runs agree
- **WHEN** the existing eval runner is invoked twice for Darjeeling in fixtures-only mode and the stable fields match
- **THEN** the designated Darjeeling baseline file is replaced with that report, and the report mode is fixture rather than a live generate

#### Scenario: Two fixtures-only runs disagree
- **WHEN** the two fixtures-only reports differ on pass rate or on any case id, passed flag, reasons, or mode
- **THEN** the designated baseline file is left unchanged and the metrics doc records the disagreeing case ids

#### Scenario: Live generate is not the baseline
- **WHEN** the Slice 0 baseline is frozen
- **THEN** it is not a copy of the retired live report at git sha `3b58df2`, and no live planner generate is required

### Requirement: Unmeasured metrics stay unlabeled as numbers
`docs/v8.2/baseline_metrics.md` MUST list the measured fixtures-only pass rate and MUST mark each of the following as unmeasured: invalid-trip rate, duplicate rate, coherence, schedule feasibility, p50 latency, p95 latency, LLM calls per trip, tokens per trip, cost per trip, OSRM or geo fallback rate, and persistence failures. The doc MUST also record the retired live report's git sha, timestamp, and pass rate. It MUST NOT invent a value for an unmeasured metric.

#### Scenario: Metrics doc after a matching pair
- **WHEN** the two fixtures-only runs agree and the baseline file is replaced
- **THEN** the metrics doc shows the measured pass rate, the retired live report identity, and every metric in the unmeasured list with no numeric substitute

#### Scenario: A missing fixture field is not treated as zero
- **WHEN** a golden fixture has no latency, token, cost, or schedule field
- **THEN** the metrics doc marks the related metric unmeasured and does not write zero
