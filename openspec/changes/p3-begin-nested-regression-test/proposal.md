## Why

Step 3.5 (v2) requires a real-session regression proving `session.begin_nested()` isolates a mid-batch DB write failure so later places still succeed. Current `tests/scripts/test_p3_scripts.py` only mocks the session, so Postgres transaction-abort behavior is never exercised and the SAVEPOINT guard can regress unnoticed.

## What Changes

- Add a pytest that uses the real `db_session` fixture (test Postgres), not `AsyncMock`
- Force `PlaceRepository.update` (or equivalent write path used by `enrich_places`) to raise on the second place only
- Assert places #1 and #3 still persist successfully when `begin_nested()` is present
- Document that a mock-session test is insufficient for this failure class
- No production code changes expected unless the regression reveals a real bug

## Capabilities

### New Capabilities

- `enrich-batch-savepoint`: Real-DB regression coverage for per-place SAVEPOINT isolation during batch enrichment

### Modified Capabilities

- (none — behavior already specified in `docs/steps/step3.md` Step 3.5; this closes the test gap)

## Impact

- `tests/scripts/test_p3_scripts.py` (new test)
- Uses existing `db_session` / `wandr_test` fixtures from `tests/conftest.py`
- No API, schema, or dependency changes
- AGENT.md: tests may exercise defensive mechanisms; no exploit payloads
- Non-goals: re-running live LLM enrich; changing `enrich_places.py` control flow unless the test fails for a real defect
