## Context

V0–V3 are shipped (`docs/context.md`): `query_points` migration, Langfuse/usage observability, golden harness. Search still lives in `src/search/client.py` + `places_index.py` against dense-only collection `places`, with `_canonical_text` = `summary` + `enriched_tags` only. Planner tool `search_places` consumes `PlaceSearchResult.place_id` only; geo fallback remains in the planner tool layer. SSOT steps: `docs/v2_blueprint.md` V4–V5; package decisions: `docs/next_version.md`. See `proposal.md` for why.

## Goals / Non-Goals

**Goals:**
- V4: name (± category) in canonical text so sparse/dense can match exact place tokens.
- V5: pure-Python sparse + `places_v2` named vectors + server-side RRF; single collection accessor; kill-switch dense-only path.
- Prove with pytest + reindex + golden harness / real API generate path before flipping traffic.
- Keep HTTP/SSE/FE contracts byte-compatible.

**Non-Goals:**
- V6 cross-encoder, embedding model bumps, or fusion diagnostics beyond optional fail-soft logs.
- Frontend code or OpenAPI shape changes.
- Mutating live `places` schema in place; deleting legacy collection before soak.
- New pip packages (`fastembed`, `rank-bm25`).

## Decisions

### D1 — Expand `_canonical_text` before enabling RRF (V4 first)
- **Choice:** Include `name` and optionally `category` with existing summary + enriched_tags; never raw OSM tags.
- **Why:** Hybrid without name tokens under-delivers on vocabulary-mismatch (blueprint order lock).
- **Alternatives:** Ship RRF first → rejected (BM25 blind to “Tiger Hill”-style queries).

### D2 — Dual collection `places_v2`, not in-place schema change
- **Choice:** New collection with `vectors_config.dense` + `sparse_vectors_config.bm25`; flip via accessor/env.
- **Why:** Principle 16 — never mutate live unnamed `places`; rollback = env flip.
- **Alternatives:** Recreate `places` in place → rejected (downtime / no easy soak).

### D3 — Single `places_collection()` accessor
- **Choice:** One function used by ensure, upsert, search, `count_indexed`.
- **Why:** Prevent split-brain when env flips mid-deploy.
- **Alternatives:** Four independent settings reads with mixed defaults → rejected.

### D4 — Pure-Python BM25-style sparse in `src/search/sparse.py`
- **Choice:** Tokenize + term weights; query-side without corpus IDF OK for MVP; `is_sparse_available` gate mirroring embeddings.
- **Why:** No image/boot cost; locked in `docs/next_version.md`.
- **Alternatives:** `fastembed` sparse → deferred; `rank-bm25` → rejected (not a Qdrant sparse encoder).

### D5 — Server-side RRF via Qdrant Prefetch + FusionQuery
- **Choice:** Dual prefetch (dense + bm25), `FusionQuery(RRF)`, `SEARCH_RRF_K` from settings (default 60).
- **Why:** Keeps fusion in Qdrant; sparse off → dense-only prefetch ≈ V1 path.
- **Alternatives:** Client-side RRF → more code / harder to keep parity with Qdrant.

### D6 — Frontend: no change
- **Choice:** Document explicitly; no FE PR.
- **Why:** Principle 17 / `docs/FE_guide.md` — ranking internals behind `place_id`; envelopes unchanged. Optional product note: same prompt may yield different POI ordering after cutover (quality, not contract).

### D7 — Validation ladder
1. Unit/pytest (`tests/search`, settings).
2. Reindex destination(s) into v2 (`scripts/index_places.py`).
3. Golden harness `scripts/run_evals.py` (must_include / no_geo_fallback) against real generate + FakeRouting as today.
4. Optional live HTTP/SSE generate smoke for Darjeeling.
5. Only then flip accessor to v2; soak; retain legacy.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Flip to empty/partial v2 → empty search → geo fallback / worse trips | Harness + index count gate before flip; never flip empty in prod |
| Ranking changes surprise stakeholders | Not a contract break; communicate quality delta; rollback env |
| Sparse encode bugs take down search | Kill-switch `SEARCH_SPARSE_ENABLED=false`; encode failure → dense-only |
| Name in dense text shifts embedding space | Expected; reindex required; harness catches regressions |
| bm25-only points invisible under dense-only | Documented fail-soft; prefer skipping points with no dense vector |
| Split-brain collection names | Mandatory single accessor |

## Migration Plan

```
V4  Expand _canonical_text → reindex (still on current collection or prepare for v2)
V5.1 Settings + places_collection()
V5.2 sparse.py + unit tests
V5.3 ensure named vectors for places_v2 (do not break places)
V5.4 Index path named vectors → index_places --destination …
V5.5 Query path RRF + dense-only degradation
V5.6 Harness green → flip accessor → soak → delete legacy later
```

**Rollback:** `SEARCH_SPARSE_ENABLED=false` and/or point accessor back to validated collection; no Alembic migrations.

**Frontend:** None required. If a sibling FE repo documents “deterministic POI lists,” update that docs note only — not UI code.

## Open Questions

- Whether to include `category` in V4 canonical text by default vs name-only (blueprint allows ±); default **include category** unless harness shows noise — reversible string change + reindex.
- Exact default after cutover for `QDRANT_PLACES_COLLECTION` vs accessor reading V2 — implement accessor to prefer V2 when an explicit “use v2” setting or when `QDRANT_PLACES_COLLECTION` is set to `places_v2`; record the chosen env shape in tasks during apply without inventing extra public APIs.
