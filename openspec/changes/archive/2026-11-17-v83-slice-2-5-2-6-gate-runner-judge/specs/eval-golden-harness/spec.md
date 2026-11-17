## MODIFIED Requirements

### Requirement: Golden load does not change scoring or the gate
Loading a golden case MUST NOT change how a generation result is scored, MUST NOT change baseline file contents by itself, and MUST NOT drop a quarantined case from the loaded set. A quarantined flag is data for the regression gate. The loader MUST NOT skip the case. Gate exclusion of quarantined cases is owned by the regression gate, not by the loader.

#### Scenario: Quarantined case is still returned
- **WHEN** a destination folder contains one valid quarantined case and one valid non-quarantined case
- **THEN** the load returns both cases

#### Scenario: Scoring keys stay the existing set
- **WHEN** a valid case asserts `validation_passed`, `max_days`, `min_places_per_day`, `readiness_score_min`, `no_geo_fallback`, and `max_tool_calls`
- **THEN** the load accepts the case and does not add or remove assertion keys

### Requirement: Baseline diff gates regressions
The runner SHALL compare a new run against a designated baseline report and exit non-zero when any previously-passing **non-quarantined** case regresses to fail. Each such regression MUST be printed with the code `REGRESSION` and the case id. A `--update-baseline` mode SHALL freeze the current run as the new baseline explicitly. A run without that flag MUST NOT modify baseline files. Aggregate pass rate in the report MUST be computed over non-quarantined cases for the gate; quarantined outcomes MAY appear in a separate report section.

#### Scenario: Regression exits non-zero
- **WHEN** a non-quarantined case passed in the baseline but fails in the new run
- **THEN** the runner prints a `REGRESSION` line for that case and exits non-zero

#### Scenario: All-pass run exits zero
- **WHEN** every non-quarantined case passes identically to baseline
- **THEN** the runner exits zero

#### Scenario: Baseline update is explicit
- **WHEN** the runner is invoked with the update-baseline flag
- **THEN** the current run replaces the stored baseline and the command exits zero

#### Scenario: Quarantined regression is not a gate fail
- **WHEN** only a quarantined case moves from pass to fail and every non-quarantined case matches baseline
- **THEN** the runner exits zero
