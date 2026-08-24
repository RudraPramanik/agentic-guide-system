## Context

`docs/next_version.md` (Blueprint v7.0 hybrid search + v7.1 observability/eval harness) was reviewed against the codebase on 2026-08-24. The plan's architecture claims all verified correct; five factual corrections and two explicit package decisions emerged. This change captures those corrections **in the plan document only** — the product build itself is out of scope here. See proposal.md for the full delta list.

## Goals / Non-Goals

**Goals:**
- Make `docs/next_version.md` implementation-ready: every stage's "proof" must actually be achievable as written.
- Record package decisions (BM25 encoder, eval runner) with rationale + revisit triggers so they are decisions, not dogma.
- Preserve both parts' independence and shippability — corrections change *how*, not *what* or *order*.

**Non-Goals:**
- Implementing any v7.0/v7.1 stage.
- Changing stage ordering, scope, or resilience contracts of either part.
- Re-opening settled architecture (Router→Service→Repository, LLM gateway exclusivity, fail-soft contracts).

## Decisions

### D1 — Correct the Stage 1 test count to three, not one
The plan said "update the one pinned test." Codebase reality: `tests/search/test_places_index.py` has three tests mocking `mock_client.search` (`test_search_places_includes_destination_filter`, `test_search_places_returns_empty_on_qdrant_error`, `test_search_places_short_circuits_on_empty_embedding`). All three migrate to `query_points` mocks or Stage 1 cannot go green. Alternative considered: leave one behind and fix later — rejected, breaks the stage's own proof gate.

### D2 — Single collection-name accessor
`QDRANT_PLACES_COLLECTION` is referenced in four places across `client.py` + `places_index.py`. Introduce one accessor (`places_collection() -> str`) reading the V2 setting; route all four through it. Without this, rollback risks split-brain (create v2 but search v1). Alternative: string-replace each site — rejected, four chances to miss one.

### D3 — Conditional vector-dict construction on upsert
Named vectors reject empty dense arrays. Upsert builds the vector dict conditionally (`dense` only when non-empty, `bm25` only when non-empty); skip point only when dict is empty. Document bm25-only points as invisible to dense-only degradation — acceptable fail-soft behavior, not a bug.

### D4 — Pure-Python BM25 stays (package decision)
| Candidate | Verdict | Reason |
|---|---|---|
| `rank-bm25` | ❌ | In-memory ranker, not a sparse-vector encoder; corpus-bound IDF dies at script↔server boundary |
| `fastembed` | ⚠️ deferred | Proper IDF but ~150MB+ image cost + boot-time model download — contradicts prod-image constraints |
| Pure-Python | ✅ | Query-side-without-IDF is standard; zero deps; solves nothing extra |

Revisit triggers (all three required): BM25 recall materially below dense in evals AND image/boot cost accepted AND Stage 3 diagnostics confirm vocabulary mismatch is dominant miss mode.

### D5 — Hand-rolled eval runner stays (package decision)
Harness is glue around our own `PlannerService.generate(routing=...)` + property assertions + baseline diff (~200 lines). `deepeval`/`ragas` target RAG-shaped pipelines and would fight TravelState-based assertions. Revisit trigger: LLM-as-judge scoring introduced (already evidence-gated).

### D6 — Explicit `TravelState.token_usage` addition
`src/planner/graph/state.py` declares `llm_retry_count` but not `token_usage`; `EvaluationService.record_generation` already reads it. Part 2 Stage 2 now explicitly requires adding the field to `TravelState` and seeding `"token_usage": {}` in `_initial_state()`.

### D7 — Retry double-count reconciliation
`agent.py` (and `parse_preferences.py`, `write_narrative.py`) already crudely increment `llm_retry_count` on `WandrLLMError`. Stage 1's honest per-call capture replaces these increments so counts aren't double-counted once both mechanisms coexist.

### D8 — Wire `flush_tracer()` at lifespan shutdown
Function exists in `src/core/observability/tracing.py`, currently unused. Part 2 Stage 3 calls it from lifespan shutdown once tracing is wired — prevents dropped tail events on process exit.

## Risks / Trade-offs

- [Plan doc drifts again if codebase changes before v7 work starts] → Corrections cite exact file/line evidence; re-run review if any cited file changes before implementation begins.
- [Package decisions could feel premature without eval data] → Both carry explicit revisit triggers tied to future evidence, so deferral is reversible, not permanent.
- [Docs-only change has no runtime proof] → Proof is the corrected document itself: three-test count matches actual test file, accessor rule covers all four reference sites, `TravelState` gap explicitly named.

## Migration Plan

Docs-only. No deploy, no rollback beyond git revert of `docs/next_version.md`.

## Open Questions

None — all corrections were verified against current code before capture.
