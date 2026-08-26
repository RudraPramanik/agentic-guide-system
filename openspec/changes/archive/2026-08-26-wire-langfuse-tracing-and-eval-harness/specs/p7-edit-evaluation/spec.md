## ADDED Requirements

### Requirement: Evaluation rows record real token usage
The evaluation write path SHALL persist actual cumulative token usage (prompt/completion/total) and LLM retry count observed during a generation into the existing `TripEvaluation` columns. When no LLM calls occurred, `token_usage` SHALL be written as an empty/zero value rather than remaining never-populated.

#### Scenario: Token usage populated after generation with LLM calls
- **WHEN** a generation completes that made one or more LLM gateway calls
- **THEN** the latest `TripEvaluation` row for the run has non-empty `token_usage` totals matching the sum of captured per-call usage

#### Scenario: Retry count reflects gateway retries
- **WHEN** the LLM gateway performed retries before success or exhaustion during a generation
- **THEN** the written `llm_retry_count` is greater than zero and equals the number of retry attempts observed
