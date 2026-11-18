## ADDED Requirements

### Requirement: check_readiness forwards the trip length and still warns

`check_readiness`, and the pre-graph readiness read that copies a score onto planner state, MUST pass the trip day count into destination readiness. When the generate request includes `days`, that value MUST be used. When the generate request omits `days`, both call sites MUST pass 3, the same default `parse_preferences` already writes onto state. They MUST NOT pass 1 for an omitted generate day count, because the trip will be planned as 3 days. When `READINESS_V2_ENABLED` is false, that day count MUST NOT change the score relative to today's counter formula.

A score below `PLANNER_MIN_READINESS_SCORE` MUST still return `ok=True` with a warning. The tool MUST NOT fail the generate run because the V2 tier is `limited` or `sparse`. The tool MUST NOT add a field to the tool result beyond the keys it returns today.

#### Scenario: Three-day state is forwarded

- **WHEN** planner state has `days` equal to 3 and the readiness flag is true
- **THEN** the readiness call receives day count 3

#### Scenario: Omitted generate days uses the planner default

- **WHEN** the generate request omits `days`
- **THEN** the pre-graph readiness call and `check_readiness` both receive day count 3

#### Scenario: Low V2 score still warns

- **WHEN** the V2 score is below `PLANNER_MIN_READINESS_SCORE`
- **THEN** `ToolResult.ok` is true and the result carries a warning

#### Scenario: Flag off score ignores days

- **WHEN** the flag is false and the same destination is checked with day count 1 and day count 3
- **THEN** both calls store the same readiness score
