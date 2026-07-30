## Why

P2 delivered place persistence, destination readiness scoring, and public HTTP endpoints, but the place knowledge layer (LLM enrichment + Qdrant semantic search) is still stub-only. The first draft of `docs/steps/step3.md` (v1) contained correctness bugs that would ship as “tests green, runtime wrong” — schema corruption of OSM tags, stale availability flags, sync Qdrant under `asyncio.wait_for`, and a permanent readiness-tier gap. Hardening the P3 build prompt to v2 (and aligning OpenSpec to it) is required before any implementation pass.

## What Changes

- Replace `docs/steps/step3.md` with the **v2 hardened** P3 Cursor prompt (build order **3.0 → 3.6**), incorporating the critic Fix Log.
- Align this change’s design/specs/tasks to v2 locked decisions (not v1).
- **BREAKING (vs v1 draft only):** enrichment MUST write LLM tags to `Place.enriched_tags`, never overwrite raw OSM `Place.tags`.
- Add Step **3.0** Alembic migration for `enriched_tags`.
- Add Step **3.6** wiring `DestinationService.get_readiness()` to `is_qdrant_available()` so tier can reach `ready`.
- Lock async/resilience contracts: `AsyncQdrantClient`, function-based availability checks, `asyncio.to_thread` for encode, `begin_nested()` per batch DB write, never `.limit(0)`, batch upsert + Qdrant ground-truth `indexed_count`.

## Capabilities

### New Capabilities

- `p3-place-knowledge-layer`: Qdrant async client + collection ensure, embeddings abstraction (lifespan-loaded, thread-offloaded), LLM place enrichment into `summary`/`enriched_tags`, semantic index + destination-scoped search, enrich/index scripts, readiness search-availability wiring.

### Modified Capabilities
<!-- Intentionally empty: no archived main-spec requirements yet for this capability. -->

## Impact

- Docs: `docs/steps/step3.md` becomes the sole P3 implementation source of truth (v2).
- Schema: additive `places.enriched_tags` JSONB list column (migration); raw `tags` untouched forever by enrichment.
- Runtime (once implemented from the prompt):
  - Enrichment + Qdrant indexing for planner-ready semantic retrieval.
  - Fail-soft: Qdrant/embeddings down → `search_places` returns `[]`; readiness degrades indexed component.
  - `/destinations/{id}/readiness` can reach `tier=ready` after enrich+index (was permanently capped at `limited` in P2).
- Dependencies (installed at the steps that need them): `qdrant-client`, `sentence-transformers` (pinned in the step prompt).
- Non-goals: no new HTTP routes in P3; no planner endpoint; no edit to P2 seed savepoints (already uses `begin_nested()`).
