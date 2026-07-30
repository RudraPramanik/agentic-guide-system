## Context

P2 delivered PostGIS places, destination search/readiness, and HTTP list/get. Search/enrichment modules under `src/search/` and the enrich/index scripts remain stubs. `Place.tags` is a JSONB **dict** of raw OSM tags from Overpass; `DestinationService.get_readiness()` still hardcodes `search_available=False`.

A v1 draft of `docs/steps/step3.md` proposed P3 but had correctness gaps (documented in the critic Fix Log). This design locks **v2** as the implementation contract. Canonical prompt: `docs/steps/step3.md` (hardened).

## Goals / Non-Goals

**Goals:**
- Author and lock a buildable P3 prompt (steps **3.0–3.6**) that agents can implement without inventing contracts.
- Separate raw OSM tags from LLM enriched tags (`enriched_tags`).
- Fail-soft semantic layer: `AsyncQdrantClient`, function availability checks, thread-offloaded encode, destination-scoped search returning `[]` on degradation.
- Close the P2→P3 readiness gap by feeding live `is_qdrant_available()` into `get_readiness()`.
- Batch scripts: bounded LLM concurrency, per-item SAVEPOINTs, never `.limit(0)`, `indexed_count` from Qdrant `count()`.

**Non-Goals:**
- No new P3 HTTP routes or planner tools.
- Do not change `compute_readiness` formula — only the `search_available` input.
- Do not “backport” savepoints to `scripts/seed_destination.py` (already uses `begin_nested()` in P2).
- Do not expose `enriched_tags` on `PlaceOut` in P3 unless a consumer needs it (defer).

## Decisions

### 1) Schema: `tags` vs `enriched_tags`

**Decision:** Add `Place.enriched_tags: Mapped[list]` JSONB (`default=list`, NOT NULL). Enrichment writes `summary` + `enriched_tags` only. Never assign to `place.tags`.

**Alternatives:** Reuse/overwrite `tags` (rejected — type mismatch and destroys OSM data). Rename `tags` (rejected — breaks P2 seed/API).

**Rationale:** Separates ownership: seed owns OSM dict; enrichment owns controlled-vocab list.

### 2) Availability flags are functions

**Decision:** `is_qdrant_available()` / `is_embeddings_available()` only. No `from module import some_bool`. Default `_qdrant_available = False` until `ensure_places_collection()` succeeds (pessimistic; matches embeddings).

**Alternatives:** Module-level bool import (rejected — stale binding). Shared mutable object (unnecessary complexity).

### 3) Async Qdrant + bounded ops

**Decision:** `qdrant_client.AsyncQdrantClient` only. Wrap client awaits in `asyncio.wait_for` with `QDRANT_OPERATION_TIMEOUT_SECONDS`. Tenacity retries for transient connectivity on ensure/upsert.

**Alternatives:** Sync client + `wait_for` (rejected — does not unbound the event loop).

### 4) Embeddings: lifespan load + `to_thread`

**Decision:** `ensure_embedding_model_loaded()` from lifespan (timeout, fail-soft). Every `encode` via `asyncio.to_thread`. `embed_batch` always returns parallel arrays; unavailable → `[[] for _ in texts]`.

**Alternatives:** Import-time model load (rejected — hung download, opaque side effect). Sync encode in async handlers (rejected — blocks event loop).

### 5) Enrichment: parse split + two failure modes

**Decision:** `_call_llm_and_parse` (no DB) + `enrich_place` (persist). Distinct logs for `WandrLLMError` vs malformed JSON/schema. Vocab in `src/places/constants.py` (`PLACE_TAG_VOCAB`). Empty filtered tags = valid success. Discard unknown tags (no fuzzy map).

**Alternatives:** Single method only (rejected — blocks concurrent LLM in batch). Vocab in Settings (rejected — domain constant, not deploy config).

### 6) Index: batch upsert + ground-truth count

**Decision:** `upsert_places_batch` uses `embed_batch` + one Qdrant upsert per chunk. Keep `upsert_place` for single re-index. `count_indexed(destination_id)` drives `Destination.indexed_count`. Embed text from `summary` + `enriched_tags` only. Always filter search by `destination_id`.

**Alternatives:** N sequential upserts (rejected — dead `embed_batch`, slow). Run-tally `indexed_count` (rejected — wrong under `--limit`).

### 7) Scripts: concurrency + SAVEPOINT + limit guard

**Decision:** Concurrent LLM under `ENRICH_BATCH_LLM_CONCURRENCY` semaphore; sequential DB writes with `session.begin_nested()`. `if limit and limit > 0: stmt.limit(limit)` — never `.limit(0)`. Qdrant unavailable on index → warn, exit 0, degraded counters.

### 8) Readiness wiring (Step 3.6)

**Decision:** `get_readiness` sets `search_available = is_qdrant_available()`. One-way dependency: destinations → search status only; search never imports destinations.

**Rationale:** Without this, the indexed term never contributes, so readiness understates search readiness after P3 work.

**Math caveat (do not “fix” the formula in P3):** score = `0.4*place + 0.35*enriched + 0.25*indexed`. Place+enriched alone can reach ≥ 0.7 (`ready`) without search. Qdrant-down always zeros `indexed_pct`; asserting a non-ready tier requires a gated fixture where place+enriched alone stay below 0.7.

### 9) Local Qdrant URL

**Decision:** Document host URL as `http://localhost:6335` (docker maps `6335:6333`). Config/env must match `.env.example` / compose — do not assume bare `6333` on the host.

**Implement note:** Existing `Settings.QDRANT_URL` default is currently `http://localhost:6333` (scaffold leftover). Step 3.1 changes that default to `6335` in place — no second setting.

## Risks / Trade-offs

- [Risk] Cold embedding model download exceeds load timeout → Mitigation: fail-soft + pre-bake model in image (`SENTENCE_TRANSFORMERS_HOME`); document in context/runbook.
- [Risk] Concurrent LLM hits provider rate limits → Mitigation: bounded semaphore (default 3); skip on `WandrLLMError`.
- [Risk] Qdrant count ≠ Postgres enriched set after partial failures → Mitigation: ground-truth count is intentional; re-run index to converge.
- [Risk] Private `_call_llm_and_parse` used from scripts → Mitigation: acceptable for P3; promote to public API later if needed.
- [Trade-off] `PlaceOut` omits `enriched_tags` in P3 → HTTP consumers keep OSM tags only until a later step.

## Migration Plan

1. Replace `docs/steps/step3.md` with v2 prompt (this change’s doc deliverable).
2. Implement in order: 3.0 migration → 3.1 client → 3.2 embeddings → 3.3 enrich → 3.4 index → 3.5 scripts → 3.6 readiness → pytest plan.
3. Rollback: drop `enriched_tags` column (additive reverse); remove lifespan ensure hooks; API remains usable with search degraded.

## Open Questions

None blocking. Optional later: expose `enriched_tags` on `PlaceOut`; payload payload-index for `destination_id` if Qdrant filter perf needs it.
