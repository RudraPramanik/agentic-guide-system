## 1. V4 — Canonical text

- [x] 1.1 Expand `_canonical_text` in `src/search/places_index.py` to include `name` and `category` (omit empty fields gracefully); keep `summary` + `enriched_tags`; never raw OSM `tags`
- [x] 1.2 Add/adjust unit coverage for canonical text composition (name present / name empty)
- [x] 1.3 Reindex at least one destination (e.g. Darjeeling) after V4 and spot-check that an exact-name query improves vs pre-change expectation
- [x] 1.4 Update `docs/context.md` Progress for V4 when 1.1–1.3 validated (`pytest tests/search -v` green)

## 2. V5 — Settings and collection accessor

- [x] 2.1 Add settings via `get_settings()`: `QDRANT_PLACES_COLLECTION_V2` (default `places_v2`), `SEARCH_SPARSE_ENABLED` (default true after cutover-ready code; keep dense-safe until harness), `SEARCH_RRF_K` (default `60`)
- [x] 2.2 Implement single `places_collection()` accessor; route ensure, upsert, search, and `count_indexed` through it (no split-brain literals)
- [x] 2.3 Add settings/accessor unit tests; confirm misconfig does not crash boot

## 3. V5 — Sparse encoder

- [x] 3.1 Add `src/search/sparse.py` with `is_sparse_available()`, `encode_sparse()`, `encode_sparse_batch()` — pure Python, no new packages
- [x] 3.2 Fail-soft: encode failure marks unavailable / returns empty per contract without raising into request path
- [x] 3.3 Unit tests for tokenize/weights, empty input, and unavailable path

## 4. V5 — Collection ensure (named vectors)

- [x] 4.1 Update `ensure_places_collection` so when accessor targets V2 it creates/ensures `dense` + sparse `bm25` configs sized to `PLACES_EMBEDDING_DIM`; do not mutate legacy `places` schema in place
- [x] 4.2 Preserve fail-soft lifespan behavior (Qdrant down → `is_qdrant_available()=False`, app boots)
- [x] 4.3 Tests or smoke for ensure path with mocked Qdrant client

## 5. V5 — Index and query hybrid path

- [x] 5.1 Upsert path: named vectors `{"dense": ..., "bm25": ...}` when available; skip points with empty dense; one batch `upsert` call per chunk (pinned test)
- [x] 5.2 Query path: dual `Prefetch` + `FusionQuery(RRF)` with `SEARCH_RRF_K`; destination filter preserved; map to `PlaceSearchResult`
- [x] 5.3 Dense-only degradation when `SEARCH_SPARSE_ENABLED=false` or sparse unavailable; Qdrant errors → `[]`
- [x] 5.4 Update existing search unit tests for hybrid/dense-only branches; `pytest tests/search -v` green

## 6. Real API validation and cutover

- [x] 6.1 Index V2 for target destination(s): `scripts/index_places.py` (confirm `count_indexed` matches Qdrant)
- [ ] 6.2 Run golden harness against real stack: `scripts/run_evals.py` — `must_include_places` / `no_geo_fallback` (and related) green; exit 0 vs baseline
- [x] 6.3 Optional live generate smoke (HTTP/SSE or `PlannerService.generate`) for Darjeeling; confirm trip envelope unchanged
- [x] 6.4 Cutover checklist: harness green → flip accessor to v2 → soak; retain legacy `places`; document rollback (`SEARCH_SPARSE_ENABLED=false` and/or accessor flip)
- [x] 6.5 Rollback drill under CI/local: sparse off / accessor back → dense path healthy

## 7. Frontend and docs

- [x] 7.1 Confirm no FE/OpenAPI contract changes required (HTTP paths, DTO envelopes, SSE names per `docs/FE_guide.md`); note only that ranking quality may change for the same prompt
- [x] 7.2 Update `docs/context.md` when V5 validated (Last updated, Next step → V6 or deferred, Progress V4–V5 ✅, Implemented modules for `sparse.py` / accessor)
- [x] 7.3 Guardrail check: no new packages; all env via `get_settings()`; planner tool `candidate_pois` / place_id contract unchanged
