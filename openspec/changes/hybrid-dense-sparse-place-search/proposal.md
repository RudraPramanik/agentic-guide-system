## Why

V0–V3 are done: CI, `query_points`, observability, and the golden harness gate retrieval changes. Place search still embeds only `summary` + `enriched_tags`, so exact-name / typo queries under-deliver, and ranking is dense-only. V4–V5 (SSOT: `docs/v2_blueprint.md`) expand indexed text, then cut over to hybrid dense + sparse (BM25-style) with server-side RRF on a dual collection (`places_v2`) — without changing HTTP, SSE, or planner tool contracts.

## What Changes

- **V4:** Expand `_canonical_text` to include place `name` (± `category`); keep `enriched_tags`; never raw OSM `tags`. Requires reindex of affected destinations before relying on hybrid gains.
- **V5:** Add settings (`QDRANT_PLACES_COLLECTION_V2`, `SEARCH_SPARSE_ENABLED`, `SEARCH_RRF_K`) and a single `places_collection()` accessor for ensure / upsert / search / count.
- **V5:** New pure-Python `src/search/sparse.py` (`is_sparse_available`, `encode_sparse`, `encode_sparse_batch`) — no new packages.
- **V5:** Ensure/create named-vector collection `places_v2` (`dense` + sparse `bm25`); index upserts both vectors when available; query uses dual `Prefetch` + `FusionQuery(RRF)` with dense-only degradation when sparse is off/unavailable.
- **V5 cutover:** Index → harness green against v2 → flip accessor → soak; keep legacy `places` until validated. Rollback via env (`SEARCH_SPARSE_ENABLED=false` and/or accessor flip).
- **Validation:** Unit/pytest for search + settings; reindex + golden harness (`scripts/run_evals.py`) against real Qdrant/API path; optional live generate smoke. Ranking may change; APIs must not.
- **Frontend:** No contract or FE code changes required (principle 17 / `docs/FE_guide.md`). Optional ops note only: after cutover, POI ranking quality may differ for the same prompt — UI still consumes the same trip/SSE shapes.

**Non-goals:** V6 polish (cross-encoder, fusion diagnostics beyond fail-soft logs); fastembed / `rank-bm25`; FE UI work; mutating live unnamed `places` in place; new HTTP fields; package upgrades.

## Capabilities

### New Capabilities
- `hybrid-dense-sparse-search`: Sparse encoder module, named-vector `places_v2` collection lifecycle, hybrid RRF query path, kill-switches, and dual-collection cutover/rollback.

### Modified Capabilities
- `p3-place-knowledge-layer`: Canonical embed text MUST include `name` (± `category`); all collection references MUST go through one settings-backed accessor; search MAY fuse dense+sparse while preserving `PlaceSearchResult` / destination filter / fail-soft `[]` contracts.

## Impact

- **Code:** `src/search/places_index.py`, `src/search/client.py`, new `src/search/sparse.py`, `src/config.py` / settings; tests under `tests/search/`; index scripts unchanged in CLI shape (`scripts/index_places.py` still works via accessor).
- **APIs / FE:** None — planner tool `search_places` still returns place IDs; HTTP/SSE/trips envelopes unchanged. Frontend: **no required changes**.
- **Deps:** None (pure-Python sparse). Keep existing `qdrant-client` APIs (`Prefetch`, `FusionQuery`).
- **Ops:** Env vars for v2 collection + sparse kill-switch; must reindex before flipping traffic to empty/partial v2; golden harness gates cutover.
- **AGENT.md:** LLM only via gateway; all env via `get_settings()`; no new packages without requirements + why-comment; fail-soft preserved.
- **Docs:** Update `docs/context.md` when V4 then V5 are validated; cite `docs/v2_blueprint.md` V4–V5.
