## Purpose

SAVEPOINT isolation for enrichment batch DB writes so one place failure does not abort the rest of the batch.

## Requirements

### Requirement: Enrich batch isolates per-place DB write failures with SAVEPOINTs

The enrichment batch path SHALL wrap each place’s DB write in `session.begin_nested()` so a write failure on one place does not abort subsequent places in the same outer transaction. Test coverage for this behavior MUST use a real Postgres-backed session (`wandr_test` / `db_session`), not an `AsyncMock` session.

#### Scenario: Mid-batch write failure does not poison later places

- **WHEN** `enrich_places` processes three places whose LLM parse succeeds for all three
- **AND** the second place’s repository update raises a DB/write error inside its nested transaction
- **THEN** the first and third places’ enrichment writes MUST still be visible after the batch
- **AND** the second place MUST NOT retain a successful enrichment write from that batch
- **AND** the reported success count MUST be `2`

#### Scenario: Mock sessions are insufficient for this regression

- **WHEN** documenting or reviewing coverage for SAVEPOINT isolation
- **THEN** a test that only mocks `session.begin_nested` or uses `AsyncMock` for the session MUST NOT be treated as satisfying this requirement
- **AND** the suite MUST include at least one real-session test as above
