# eval-regression-gate Specification

## Purpose

Deterministic golden-suite regression gate: quarantine exclusion, named baseline diffs with tolerance bands for measured metrics only, explicit baseline updates, and a seeded non-zero exit on regression.

## Requirements

### Requirement: Quarantined cases are excluded from the gate
The gate pass rate and baseline regression comparison MUST use only cases with `quarantined` equal to false. Quarantined cases MUST still be scored and MUST appear in the run report under a separate quarantined bucket. A quarantined case that fails MUST NOT by itself make the gate exit non-zero. The loader MUST continue to return quarantined cases in the loaded set.

#### Scenario: Quarantined fail does not fail the gate
- **WHEN** one non-quarantined case passes and one quarantined case fails
- **THEN** the gate pass rate is `1.0`, the report lists the quarantined failure in the quarantined bucket, and the process exits zero if the baseline has no non-quarantined regression

#### Scenario: Non-quarantined regression still fails the gate
- **WHEN** a non-quarantined case passed in the baseline and fails in the new run
- **THEN** the process exits non-zero even if every quarantined case passes

### Requirement: Baseline regressions are named and exit non-zero
When a non-quarantined case passed in the stored baseline and fails in the current run, the runner MUST print a line that contains the code `REGRESSION` and the case id, and MUST exit non-zero. A normal run without `--update-baseline` MUST NOT write or replace any file under `evals/baselines/`.

#### Scenario: Seeded regression prints REGRESSION and exits non-zero
- **WHEN** a test supplies a baseline where case `seed-pass` passed and a run where `seed-pass` fails
- **THEN** the gate output contains `REGRESSION` and `seed-pass`, and the exit code is non-zero

#### Scenario: Matching non-quarantined suite exits zero
- **WHEN** every non-quarantined case matches the baseline pass/fail outcome
- **THEN** the process exits zero

#### Scenario: Update baseline is required to freeze
- **WHEN** the runner finishes without the update-baseline flag
- **THEN** the stored baseline file bytes are unchanged

### Requirement: Tolerance bands gate only measured metrics
The runner MAY attach aggregate metric values to the run report by calling the existing pure metric functions. A tolerance-banded metric MUST hard-fail the gate only when a measured baseline variance for that metric exists in the committed tolerance metadata. A metric marked unmeasured in `docs/v8.2/baseline_metrics.md` or absent from tolerance metadata MUST be reported and MUST NOT change the exit code. Case-level pass/fail regression for non-quarantined cases remains a hard gate regardless of tolerance metadata.

#### Scenario: Unmeasured band does not fail the gate
- **WHEN** the report includes a coherence or latency aggregate and no measured tolerance exists for that metric
- **THEN** the process does not exit non-zero solely because of that aggregate

#### Scenario: Measured band regression fails the gate
- **WHEN** a metric has committed tolerance metadata and the run is worse than baseline minus that tolerance
- **THEN** the process exits non-zero and the output names that metric

### Requirement: Explicit update-baseline freezes the current gate report
Invoking the runner with `--update-baseline` MUST replace `evals/baselines/<destination>.json` with the current run report (including gate pass rate over non-quarantined cases) and MUST exit zero. It MUST NOT require a separate manual file edit.

#### Scenario: Update writes the baseline
- **WHEN** the runner is invoked with `--update-baseline` after a successful score pass
- **THEN** the destination baseline file equals the current report and the exit code is zero
