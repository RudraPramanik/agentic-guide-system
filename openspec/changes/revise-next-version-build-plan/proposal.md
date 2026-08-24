## Why

The v7.0/v7.1 build plan (`docs/next_version.md`) was reviewed against the actual codebase (2026-08-24). The review found five factual corrections — including one plan-internal contradiction ("update the one pinned test" when three tests mock `client.search`) and one missing state-schema edit (`token_usage` absent from `TravelState` despite `EvaluationService` reading it). It also produced two explicit package decisions (BM25 encoder, eval harness) that were previously implicit. The plan document must be corrected before implementation starts, or Stage 1 will not be green and Stage 2 of Part 2 will silently skip a required edit.

## What Changes

- **Docs only** — revises `docs/next_version.md`; no product code, no migrations, no dependency changes.
- Correct Stage 1 test count: **three** pinned tests mock `mock_client.search` (`test_search_places_includes_destination_filter`, `test_search_places_returns_empty_on_qdrant_error`, `test_search_places_short_circuits_on_empty_embedding`) — all migrate to `query_points`, not one.
- Add **single accessor rule** for collection naming: route all four `QDRANT_PLACES_COLLECTION` references through one accessor reading the V2 setting, eliminating split-brain rollback risk.
- Add **partial-vector upsert rule**: named vectors require conditional dict construction; skip a point only when both dense and bm25 are empty; document bm25-only points as invisible to dense-only degradation.
- Record **package decision: pure-Python BM25 stays** (rank-bm25 rejected as wrong tool; fastembed deferred with explicit revisit triggers).
- Record **package decision: hand-rolled eval runner stays** (deepeval/ragas rejected as RAG-shaped; revisit trigger = LLM-as-judge scoring).
- Correct Part 2 Stage 2: add explicit requirement to add `token_usage` to `TravelState` + seed it in `_initial_state()`.
- Add retry double-count reconciliation note: replace crude `llm_retry_count + 1` increments in `agent.py` / `parse_preferences.py` / `write_narrative.py` with honest per-call counts.
- Add `flush_tracer()` lifespan-shutdown wiring to Part 2 Stage 3.

## Capabilities

### New Capabilities

(none — docs-only change)

### Modified Capabilities

(none — no spec-level behavior changes; `.openspec.yaml` sets `skip_specs: true`)

## Impact

- **Files changed:** `docs/next_version.md` only.
- **No impact on:** product code, tests, dependencies, DB schema, API surface, planner tool contracts.
- **Downstream effect:** implementation of v7.0/v7.1 proceeds against a corrected plan; prevents a red Stage 1 and a silently-missed `TravelState` edit in Part 2 Stage 2.

## Non-goals

- No implementation of any v7.0/v7.1 stage in this change.
- No re-litigating stage ordering or scope — both parts remain independently shippable as planned.
