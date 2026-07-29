## Context

P3 Step 3.5 already wraps each enrich-batch DB write in `session.begin_nested()` (`scripts/enrich_places.py`). Without a real Postgres regression test, removing that SAVEPOINT still leaves the mock-based “continue on parse None” test green while mid-batch write failures poison the outer transaction (asyncpg: current transaction is aborted).

Cite: `docs/steps/step3.md` Fix Log #8 and Testing Plan ★ NEW for `tests/scripts/test_p3_scripts.py`.

## Goals / Non-Goals

**Goals:**

- Prove with `wandr_test` that a raised error on place #2’s write does not prevent places #1 and #3 from succeeding when SAVEPOINTs are used
- Keep the test deterministic: no live LLM; patch `_call_llm_and_parse` to return valid parsed enrichment for all three places

**Non-Goals:**

- Changing enrich concurrency, LLM parsing, or Qdrant indexing
- Replacing existing mock tests (they still cover parse-None continue and limit(0))
- Live Gemini/NVIDIA enrich runs

## Decisions

1. **Real `db_session`, not AsyncMock**  
   Only a real engine reproduces transaction abort after a failed flush. Seed three `Place` rows + one `Destination` in the test DB (same patterns as other repository tests).

2. **Fail the write path, not the LLM path**  
   Patch `PlaceService._call_llm_and_parse` to always succeed; patch `PlaceRepository.update` (or the exact call site inside the nested block) with a side_effect that raises on the second invocation only. That isolates SAVEPOINT behavior from LLM skip logic.

3. **Assert DB state after the batch**  
   After `enrich_places(...)`, query summaries/enriched_tags for places 1 and 3 — must be persisted. Place 2 must remain unenriched (or rolled back to prior state). Success count should be 2.

4. **Alternatives considered**  
   - Mock `begin_nested` and assert it was called → does not prove Postgres semantics. Rejected.  
   - Force a real CHECK constraint violation → heavier fixture setup; explicit raise on update is clearer and still hits SAVEPOINT rollback.

## Risks / Trade-offs

- [Test flaky if session fixture autocommits oddly] → Follow existing `db_session` rollback-per-test pattern in `conftest.py`
- [Patch target drifts if enrich script refactor moves update call] → Patch the symbol used inside `scripts.enrich_places` / `PlaceService.repo.update` at the call site the script uses
- [Slightly slower than pure mocks] → Acceptable; one integration test in the scripts suite
