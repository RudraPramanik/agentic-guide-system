## MODIFIED Requirements

### Requirement: Metrics are pure and do not change the golden verdict
Each metric MUST be a pure function of its inputs. It MUST NOT call an LLM, the network, or a database, and it MUST NOT mutate inputs. The same inputs MUST return the same number twice. These functions MUST NOT add or remove golden assertion keys and MUST NOT change how `score_case` decides pass or fail for an existing golden case. The regression gate MAY call these functions to attach aggregates or tolerance-band comparisons to a run report. That call MUST NOT alter per-case assertion keys or replace `score_case`.

#### Scenario: Repeated call matches
- **WHEN** a metric is called twice with the same inputs
- **THEN** both results are equal

#### Scenario: Golden verdict is unchanged
- **WHEN** an existing Darjeeling case is scored by `score_case` before and after the gate calls a metric for the report
- **THEN** the pass/fail verdict and the reasons for that case stay the same

#### Scenario: Gate may read a metric without changing assertions
- **WHEN** the gate attaches a duplicate-stop or feasibility aggregate from a metric function to the run report
- **THEN** the case assertion key set is unchanged and `score_case` still owns the per-case verdict
