## 1. Part 1 (v7.0) plan corrections

- [ ] 1.1 Stage 1: replace "update the one pinned test" with the three-test list (`test_search_places_includes_destination_filter`, `test_search_places_returns_empty_on_qdrant_error`, `test_search_places_short_circuits_on_empty_embedding`) — all migrate to `query_points` mocks
- [ ] 1.2 Stage 2: add single-accessor rule — one `places_collection() -> str` accessor reading `QDRANT_PLACES_COLLECTION_V2`, routing all four reference sites (`ensure_places_collection()`, `_upsert_points_impl()`, `search_places()`, `count_indexed()`)
- [ ] 1.3 Stage 2: add partial-vector upsert rule — conditional dict construction, skip only when both dense and bm25 empty; document bm25-only points as invisible to dense-only degradation
- [ ] 1.4 Stage 2: record package decision table for BM25 (pure-Python chosen; rank-bm25 rejected; fastembed deferred with three revisit triggers)

## 2. Part 2 (v7.1) plan corrections

- [ ] 2.1 Stage 2: add explicit requirement — add `token_usage` field to `TravelState` and seed `"token_usage": {}` in `_initial_state()` alongside `"llm_retry_count": 0`
- [ ] 2.2 Stage 2: add reconciliation note — replace crude `llm_retry_count + 1` increments in `agent.py`, `parse_preferences.py`, `write_narrative.py` with honest per-call counts from Stage 1
- [ ] 2.3 Stage 3: add task to call existing-but-unused `flush_tracer()` from lifespan shutdown once tracing is wired
- [ ] 2.4 Stage 4: record package decision table for eval runner (hand-rolled chosen; deepeval/ragas rejected with RAG-shape rationale; revisit trigger = LLM-as-judge scoring)

## 3. Verification

- [ ] 3.1 Re-read corrected `docs/next_version.md` end-to-end; confirm every stage's "✅ Proof" is achievable as written against current code
- [ ] 3.2 Confirm no product code, tests, requirements, or migrations were touched by this change (`git status` shows only docs + openspec artifacts)
