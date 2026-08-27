# Blueprint v7.0 — Hybrid Dense + Sparse Place Search (BM25-style)
> Extends `docs/blueprint_final.md` (v6.1). This file holds **why / package decisions / detailed stage notes** for the next version's retrieval + observability upgrade.
>
> **Build SSOT (step-by-step phases V0–V6):** [`docs/v2_blueprint.md`](v2_blueprint.md) — use that file to execute work (same shape as `blueprint_final.md`).
> Scope: upgrade place retrieval from pure dense vector search to **hybrid dense + sparse (BM25-style) with server-side RRF fusion** — without breaking any architecture rule, resilience contract, or existing consumer.
>
> **Supersedes nothing.** v6.1 remains the SSOT for everything not touched here.

---

## Why

| Problem today | Evidence |
|---|---|
| Vocabulary mismatch: dense embeddings miss exact tokens ("Tiger Hill", "MG Marg", typo "darjeling") | Only retrieval signal is MiniLM/Gemini cosine over `summary\nenriched_tags` |
| Rich text underused: `name`, `category`, `enriched_tags` exist but only summary+tags are embedded | `_canonical_text()` in `src/search/places_index.py` |
| Fallback is binary: Qdrant hits OR PostGIS radius — no fusion of weak/strong signals | `src/planner/tools/search_places.py` (`if not places:`) |
| Legacy deprecated API in use | `client.search(query_vector=...)` on `qdrant-client==1.15.1` |

**Non-goals**
- No cross-encoder reranking (deferred until `evaluation/` data shows precision ordering problems).
- No new external service, no Redis/pgvector migration, no change to planner tools' I/O contracts.
- No change to embedding models or the hosted-embeddings gateway contract.
- No frontend/API surface changes.

---

## What stays untouched (architecture guarantees)

```
Router → Service → Repository      unchanged
LLM via core/llm/client.py only    unchanged (sparse encoding is local & deterministic)
Geo via src/geo/ only              unchanged
travel_engine purity               unchanged
evaluation records everything      unchanged
All env via get_settings()         unchanged
Fail-soft search contracts         extended, never removed
```

The planner tool `search_places` consumes **only `.place_id`** from `PlaceSearchResult` — ranking internals can change freely behind that seam.

---

## Implementation order (cross-part sequencing)

Both parts are internally staged, but the parts interleave. The harness (Part 2 Stage 4) must land **before** the RRF cutover (Part 1 Stage 2) so the retrieval change is proven by golden cases instead of hoped-for. CI comes first because every stage's proof gate is "pytest green" — see `docs/ci_cd_plan.md`.

```
NOW          →  minimal CI (pytest + docker build)     ← half day, docs/ci_cd_plan.md Phase A
THEN         →  P1.Stage 1  (safe under CI already)
THEN         →  P2.Stages 1→2→3→4  (observability + harness)
THEN         →  P1.Stage 2  (RRF cutover, harness-gated)
LATER        →  P1.Stage 3  (only if evidence demands)
MUCH LATER   →  full CD (auto-deploy) whenever deploy pain appears
```

| # | Work | Why this position |
|---|---|---|
| 0 | Minimal CI | Every later stage's proof assumes an automated test gate; pinned tests break silently without one |
| 1 | P1.Stage 1 | Trivial, zero behavior change; de-risks deprecated `client.search` before anything else touches that file |
| 2 | P2.Stages 1–3 | Zero-behavior-change capture first, then tracing on top of now-honest data |
| 3 | P2.Stage 4 | Golden harness = regression gate that makes the next step safe |
| 4 | P1.Stage 2 | The retrieval win — validated by the harness (`must_include_places`, `no_geo_fallback`) before/after cutover |
| 5 | P1.Stage 3 | Evidence-gated; uses harness for before/after comparison |
| — | Full CD | Deferred until deploy pain appears; no v7 stage depends on auto-deploy |

---

## Stage plan (3 stages, each independently shippable)

### Stage 1 — Deprecation-proof the query path (zero behavior change)

Migrate `client.search(query_vector=...)` → `client.query_points(...)` inside `src/search/places_index.py`.

- Same filter, same limit, same results (`QueryResponse.points[].payload/.score` shape identical).
- Update **three** pinned tests that mock `mock_client.search` (not one):
  - `test_search_places_includes_destination_filter` → assert the destination filter survives inside `query_points`
  - `test_search_places_returns_empty_on_qdrant_error`
  - `test_search_places_short_circuits_on_empty_embedding`
- ✅ Proof: pytest green; manual `search_places("photography sunrise", darjeeling_id)` returns identical ordering to pre-migration snapshot.

### Stage 2 — Sparse vectors + server-side RRF fusion (the real win)

#### Collection config (additive, named vectors)
```python
# src/search/client.py — ensure_places_collection()
vectors_config={
    "dense": qmodels.VectorParams(size=settings.PLACES_EMBEDDING_DIM,
                                  distance=qmodels.Distance.COSINE),
},
sparse_vectors_config={
    "bm25": qmodels.SparseVectorParams(),   # client-side computed BM25 weights
}
```
- New collection name from settings: `QDRANT_PLACES_COLLECTION_V2` (default `places_v2`) → zero-downtime cutover; old collection deleted after validation.
- **Single accessor rule:** `QDRANT_PLACES_COLLECTION` is referenced in four places (`ensure_places_collection()`, `_upsert_points_impl()`, `search_places()`, `count_indexed()` across `client.py` + `places_index.py`). Introduce one accessor (e.g. `def places_collection() -> str` reading the V2 setting) and route ALL four through it — rollback then truly is a one-env-var flip, with no split-brain risk of creating v2 but searching v1.
- Point IDs stay deterministic (`str(place.id)`) → re-running `scripts/index_places.py --destination X` is idempotent.

#### New module: `src/search/sparse.py`
```python
def is_sparse_available() -> bool                      # fail-soft gate, mirrors embeddings.py
def encode_sparse(text: str) -> qmodels.SparseVector   # pure-Python BM25 term weights
async def encode_sparse_batch(texts: list[str]) -> list[qmodels.SparseVector]
```

**Pure-Python BM25 — no new package.** (Blueprint principle 5: lightest viable package.)
- Tokenize: lowercase, split on non-alphanumeric, drop stopwords (small inline set), simple suffix-stem-lite (optional, keep minimal).
- IDF from a per-process corpus stat built during batch indexing; for single-query encoding use query-term weights without IDF (standard practice for sparse neural/BM25 query side).
- ~100 lines, no torch, no network — safe for the prod image (which excludes sentence-transformers deliberately).

**Package decision (reviewed 2026-08): pure-Python stays.**
| Candidate | Verdict | Why |
|---|---|---|
| `rank-bm25` | ❌ rejected | In-memory *ranker* over a pre-built corpus, not a sparse-vector encoder — can't emit Qdrant `SparseVector`s, and its corpus-bound IDF dies at the script↔server process boundary (the exact problem we design around). |
| `fastembed` (`Qdrant/bm25` sparse) | ⚠️ deferred | Only real candidate; proper IDF incl. query side. But drags ONNX Runtime + HF hub (~150MB+ image), model download at boot — contradicts why sentence-transformers is excluded from prod. |
| Pure-Python | ✅ chosen | Query-side-without-IDF is standard for this shape; zero deps; the package doesn't solve our hardest problem (cross-process IDF). |

*Revisit triggers for fastembed:* (a) retrieval evals show BM25 recall materially below dense on real queries, AND (b) we accept the image/boot cost, AND (c) Stage 3 diagnostics confirm vocabulary mismatch is the dominant miss mode. Any one alone is not enough.

#### Indexing changes (`src/search/places_index.py`)
```python
PointStruct(
    id=str(place.id),
    vector={
        "dense": dense_vector,          # unchanged embed path
        "bm25": encode_sparse(_canonical_text(place)),
    },
    payload=_payload_for(place, destination_id),
)
```
- Upsert skips a point only if BOTH vectors unavailable (today it skips if dense empty).
  - ⚠️ Named vectors require explicit dict construction — `vector={"dense": []}` is invalid. Build conditionally: include `dense` only when non-empty, `bm25` only when non-empty; skip the point only when the dict ends up empty.
  - ⚠️ A point indexed bm25-only (embeddings down, sparse up) is invisible to dense-only degradation. Acceptable fail-soft behavior — documented here, not a bug.
- Batch upsert stays ONE `client.upsert` call (pinned test).

#### Query changes — server-side fusion
```python
client.query_points(
    collection_name=settings.QDRANT_PLACES_COLLECTION_V2,
    prefetch=[
        qmodels.Prefetch(query=dense_vector, using="dense", limit=top_k * 2,
                         filter=dest_filter),
        qmodels.Prefetch(query=sparse_query_vec, using="bm25", limit=top_k * 2,
                         filter=dest_filter),
    ],
    query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
    limit=top_k,
)
```
- One round trip; latency well within existing `QDRANT_OPERATION_TIMEOUT_SECONDS = 5.0`.
- **Graceful degradation ladder:** sparse encoder unavailable → dense-only prefetch (identical to today); Qdrant down → existing geo fallback (unchanged); both fail → `[]`.

#### Settings additions (`src/config.py`)
```python
QDRANT_PLACES_COLLECTION_V2: str = "places_v2"
SEARCH_SPARSE_ENABLED: bool = True            # kill-switch for instant rollback
SEARCH_RRF_K: int = 60                        # standard RRF constant; no magic numbers in code
```

### Stage 3 — Evaluation-driven polish (conditional, evidence-gated)

Only if `TripEvaluation.tool_trace` shows `expand_poi_search` frequency or user edits concentrated on retrieval misses:
- Log per-query fusion diagnostics (dense hits vs sparse hits vs fused order) into tool_trace.
- Optional: bump local embedding model to `bge-small-en-v1.5` (still 384d — dim-compatible, reindex-only swap).
- Optional: cross-encoder rerank top-20→top-5 (new decision required; NOT pre-approved here).

---

## Resilience Contract (extends blueprint table)

| Component | Retry | Timeouts | Final Fallback |
|---|---|---|---|
| `search/sparse.py` | none (pure CPU) | N/A | `is_sparse_available()=False` → dense-only prefetch |
| `search/places_index.py` hybrid query | tenacity 2x (existing pattern) | `QDRANT_OPERATION_TIMEOUT_SECONDS` | `[]` → planner PostGIS fallback (unchanged) |
| Collection cutover | n/a | n/a | old collection retained until validated; rollback = flip `QDRANT_PLACES_COLLECTION_V2` back |

Never retry on 4xx from Qdrant (config bugs, not transient).

## Failure Boundary Summary (delta)

| Failure | Response |
|---|---|
| Sparse encoder raises | Log once, mark unavailable, dense-only search. App serves normally. |
| V2 collection missing at startup | `ensure_places_collection()` creates it (idempotent, never raises). |
| Partial points missing bm25 vector | RRF still works — sparse prefetch returns fewer candidates; no error. |
| Rollback needed | Set `SEARCH_SPARSE_ENABLED=false` or revert collection setting → dense-only behavior identical to v6.1. |

---

## Guardrail compliance checklist

- [ ] All changes confined to `src/search/`, `src/config.py`, `scripts/index_places.py`, one test file
- [ ] No litellm/groq/openai imports outside `core/llm/client.py`
- [ ] No new packages (pure-Python BM25) — if fastembed ever needed: requirements.txt + why-comment first
- [ ] No hardcoded strings/dims/collection names — all via `get_settings()`
- [ ] Fail-soft preserved at every layer; planner tool contract (`ToolResult.data.candidate_pois`) byte-identical
- [ ] `pytest tests/search tests/planner -v` green after each stage
- [ ] Re-run `scripts/index_places.py --destination Darjeeling` → indexed_count matches Qdrant count truth

## Ship proof (per stage)

1. Stage 1: pytest green + identical-result snapshot check.
2. Stage 2: seed+enrich+index Darjeeling → queries like "Tiger Hill sunrise photography" and exact-name "darjeling zoo" (typo) return expected places in top-5; `used_geo_fallback=False`; evaluation rows written.
3. Stage 3 (if triggered): before/after comparison table from TripEvaluation data.

---

---

# Blueprint v7.1 — Observability & Evaluation Harness (Langfuse + Golden Datasets)
> **Status 2026-08-27: SHIPPED** (token usage + golden harness + Langfuse generate wrap).
> Historical staged plan below — **do not treat “Problem today” or Stage 2 “token_usage is NOT in TravelState” as current facts.**
> Current truth: `docs/context.md` + `docs/v2_blueprint.md` V2–V3. `TravelState.token_usage` is seeded and persisted; `PlannerService.generate` starts/ends a Langfuse parent trace (NoOp when keys empty).
> Build SSOT remains `docs/v2_blueprint.md` V2–V3.
> Extends `docs/blueprint_final.md` (v6.1). Companion to Part 1 above — independent scope, independently shippable.
> Scope (as originally planned): light up LLM observability (token/retry capture + Langfuse tracing via the existing facade) and build an offline golden-dataset regression harness — without breaking any architecture rule, resilience contract, or existing consumer.
>
> Machine-actionable history: archived OpenSpec `wire-langfuse-tracing-and-eval-harness`; wrap completion change `fix-langfuse-generate-wrap-and-refresh-manual`.
> This section is the human-readable staged build plan (kept for audit).

## Why (historical — pre-ship)

| Problem (then) | Evidence (then) |
|---|---|
| Token usage was never recorded | `core/llm/client.py` discarded `response.usage` → `TripEvaluation.token_usage` always `{}` |
| Retry counts were fiction | `llm_retry_count` column existed; nothing wrote it |
| Tracer was dead code | `get_tracer()` had zero callers despite `langfuse` pinned + keys declared |
| No regression gate for pipeline changes | v7.0 Stage 3 promised “evaluation-driven polish” with no eval infrastructure |

**Non-goals**
- No HITL review/approval gate (implicit edit signals suffice for now).
- No LLM-as-judge scoring (evidence-gated follow-up once rule-based baselines exist).
- No Langfuse self-hosting/deployment work; no LangSmith.
- No API/frontend/tool-contract changes; no retrieval changes (Part 1 owns those).

## What stays untouched (architecture guarantees)

```
Router → Service → Repository      unchanged
LLM via core/llm/client.py only    unchanged (usage capture happens inside it)
Geo via src/geo/ only              unchanged
travel_engine purity               unchanged (scorers import validator, add nothing)
evaluation records everything      unchanged (same columns, now honestly populated)
All env via get_settings()         unchanged (LANGFUSE_* keys already declared)
Fail-soft contracts                extended (tracer failures swallowed like evaluation writes)
```

## Stage plan (4 stages, each independently shippable)

### Stage 1 — Honest token & retry capture (zero behavior change)

Inside `src/core/llm/client.py` only:
- New `LLMUsage` dataclass (prompt/completion/total tokens); capture from `response.usage` in `chat_completion`, `chat_with_tools`, `embed_texts`. Missing usage → empty usage, never raise.
- Extend `_llm_retry` bookkeeping (`before_sleep` hook) so retry attempts are countable per call.

✅ Proof: pinned tests assert return contracts byte-identical; `pytest tests/core -v` green.

### Stage 2 — Thread usage into state and evaluation

- ✅ **Done:** `token_usage` is on `TravelState` and seeded in `_initial_state()` (historical note below claimed otherwise pre-ship).
- Planner nodes accumulate per-call usage into `state["token_usage"]` (summed) and retries into `state["llm_retry_count"]`.
- (Historical) ⚠️ Pre-ship: `token_usage` was missing from `TravelState` — Stage 2 added it. Do not re-add.
- Reconcile with existing crude increment: `agent.py` already does `llm_retry_count + 1` on `WandrLLMError` (and `parse_preferences.py` / `write_narrative.py` have similar) — replace these with honest per-call counts from Stage 1 so retries aren't double-counted.
- `EvaluationService.record_generation` already reads these keys — mapping verified, columns exist, **no migration**.

✅ Proof: generate once → `trip_evaluations` row shows real token totals and retry count.

### Stage 3 — Wire Langfuse tracing (fail-soft, key-gated)

```
PlannerService.generate()
   ├─ trace start ──────────────────────────────── trace end (incl. timeout/abort paths)
   │     ├─ generation spans: gateway calls (model, tokens, latency, retries)
   │     └─ tool spans: derived post-hoc from tool_trace entries (zero tool-code changes)
```

- Trace lifecycle at service level (not router SSE queue — it drops state snapshots).
- All tracer interaction wrapped fail-soft: swallow + log-once per process, mirroring `evaluation_write_failed`.
- Empty keys (default) → `NoOpTracer` → behavior byte-identical to today, zero network traffic.
- **Kill-switch**: unset keys. **Rollback**: revert commit; no migrations involved.
- ⚠️ Keep `langfuse==2.60.10` (v2 API matches facade). Do NOT upgrade to v3 (removed `trace()` client API).
- Call existing-but-unused `flush_tracer()` from lifespan shutdown once tracing is wired.

✅ Proof: keys set locally → one trace per generate with tool + LLM spans; keys unset → identical results, no traffic; simulated tracer exception doesn't fail a generation.

### Stage 4 — Golden-dataset regression harness

**Package decision (reviewed 2026-08): hand-rolled runner stays.**
| Candidate | Verdict | Why |
|---|---|---|
| Hand-rolled (~200 lines) | ✅ chosen | Harness is glue around our own `PlannerService.generate(routing=...)` + property assertions + baseline diff — no framework needed. |
| `deepeval` / `ragas` | ❌ rejected | Built for RAG-shaped pipelines (contexts/retrievers/QA); would force cases into their dataset format and fight TravelState-based assertions. Heavy deps; some make their own LLM calls. |

*Revisit trigger:* only if Stage 3+ introduces LLM-as-judge scoring — that's where deepeval earns its weight, and it's already evidence-gated in this plan.

```
evals/
  golden/darjeeling/*.json   ← property-based cases (NEVER exact output strings)
  baselines/<dest>.json      ← frozen known-good run (git SHA + case-set hash)
  runs/<ts>-<sha>.json       ← machine-readable reports

scripts/run_evals.py         ← replay via PlannerService.generate(routing=FakeRoutingProvider...)
src/evaluation/scorers.py    ← pure scorers; feasibility delegates to trip_validator.validate_trip
```

Case shape:
```jsonc
{
  "id": "dar-001",
  "destination": "Darjeeling",
  "raw_input": "3 days, photography, sunrise spots",
  "must_include_places": ["Tiger Hill"],
  "assertions": {
    "validation_passed": true,
    "max_days": 3,
    "min_places_per_day": 3,
    "readiness_score_min": 0.6,
    "no_geo_fallback": true,
    "max_tool_calls": 10
  }
}
```

- Baseline diff: exit non-zero only when a previously-passing case regresses; `--update-baseline` explicit; stale-baseline warning via SHA/case-hash.
- LLM-unavailable mode still scores deterministic assertions (constraints, validator, fallback flags) — mirrors boot-without-LLM-key precedent.

✅ Proof: full run exits 0 vs fresh baseline; deliberately broken expectation → non-zero exit with named diff.

## Resilience Contract (delta)

| Component | Retry | Timeouts | Final Fallback |
|---|---|---|---|
| Tracer calls | none | SDK async batching | swallow + log-once; generation unaffected |
| Usage capture | none (in-response) | n/a | empty `LLMUsage` |
| Eval runner vs LLM | existing gateway retries | `PLANNER_GENERATION_TIMEOUT_SECONDS` | deterministic-only assertions still scored |

Observability is NEVER on the critical path.

## Guardrail compliance checklist

- [ ] No litellm/langfuse imports outside `core/llm/client.py` / `core/observability/tracing.py`
- [ ] No new packages (langfuse already pinned)
- [ ] All env via `get_settings()`; default-empty keys keep boot working without Langfuse
- [ ] travel_engine untouched; planner tool contracts byte-identical
- [ ] `pytest tests/core tests/planner tests/evaluation -v` green after each stage
- [ ] Evaluation write path stays fail-soft

## Relationship to Part 1 (hybrid search)

Independent but synergistic: this blueprint's harness is what makes Part 1's Stage 3 ("evaluation-driven polish") actually executable — golden cases can assert retrieval quality (`must_include_places`, `no_geo_fallback`) before/after the RRF cutover. Either part can ship first.
