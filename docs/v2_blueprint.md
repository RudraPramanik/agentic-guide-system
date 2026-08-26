# Wandr — Backend Blueprint v7.0 (Post-P7 Retrieval + Observability)
> Step-by-step build bible for the next backend version. Same shape as `docs/blueprint_final.md` (v6.1): phases, per-step proofs, resilience, fail-soft ladders.
>
> **Does not supersede v6.1.** `docs/blueprint_final.md` remains SSOT for shipped P0–P7.
> **This file is the SSOT for post-P7 / v7 build steps.** Detailed package-decision tables live in `docs/next_version.md`. CI detail: `docs/ci_cd_plan.md`.
>
> **Frontend:** unchanged by v7 — no API/FE contract changes. Wire contract still `docs/FE_guide.md`.

**Companion OpenSpec (code, not this docs change):**
| Area | Change |
|------|--------|
| Observability + golden harness | `openspec/changes/wire-langfuse-tracing-and-eval-harness/` |
| Hybrid dense+sparse search | `openspec/changes/hybrid-dense-sparse-place-search/` (fill tasks from V1/V4/V5 here) |
| Minimal CI | `docs/ci_cd_plan.md` Phase A |

---

## What's in this version

| Source | What was taken |
|--------|----------------|
| `docs/next_version.md` v7.0 | Hybrid dense + sparse (BM25-style) + server-side RRF; `places_v2` cutover; pure-Python sparse |
| `docs/next_version.md` v7.1 | Token/retry honesty; Langfuse via existing facade; golden eval harness |
| `docs/ci_cd_plan.md` | Minimal CI before any retrieval change; full CD deferred |
| Codebase review 2026-08 | Three `query_points` tests; single collection accessor; `TravelState.token_usage` gap; expand `_canonical_text` for names; `flush_tracer()` already in lifespan |
| **v7.0 principle add** | **Max fail-soft** — every new path degrades to v6.1 working behavior |

---

## Principles (inherit v6.1 + v7 deltas)

| # | Principle |
|---|-----------|
| 1–13 | All principles from `docs/blueprint_final.md` still apply |
| **14** | **Max fail-soft for v7** — sparse/Langfuse/hybrid never take down generate; each has a kill-switch or NoOp |
| **15** | **Harness before ranking change** — golden cases gate RRF cutover |
| **16** | **Dual collection cutover** — never mutate live unnamed `places` in place; validate `places_v2` then flip one accessor |
| **17** | **No API/FE delta** — planner tool contracts and HTTP envelopes stay byte-compatible |

---

## What stays untouched (architecture guarantees)

```
Router → Service → Repository      unchanged
LLM via core/llm/client.py only    unchanged (usage capture / sparse encode stay local)
Geo via src/geo/ only              unchanged
travel_engine purity               unchanged
evaluation records everything      unchanged (columns now honestly populated)
All env via get_settings()         unchanged
Fail-soft search + geo fallback    extended, never removed
HTTP / SSE / trips / auth          unchanged
```

Planner tool `search_places` consumes **only** `PlaceSearchResult.place_id` — ranking internals may change behind that seam.

---

## Implementation order (locked)

```
V0  Minimal CI (pytest + docker build)          ← docs/ci_cd_plan.md Phase A
V1  query_points migration (zero behavior)      ← safe under CI
V2  Observability (usage → state → Langfuse)    ← fail-soft / keys empty = NoOp
V3  Golden-dataset harness                      ← regression gate
V4  Expand _canonical_text (name ± category)    ← BM25 can see exact tokens
V5  Hybrid RRF + places_v2 cutover              ← harness-gated
V6  Evidence-driven polish                      ← only if evals demand
——  Full CD (ci_cd_plan Phase B)                ← MUCH LATER, deploy-pain only
```

| # | Why this position |
|---|-------------------|
| V0 | Every later proof assumes automated pytest |
| V1 | De-risk deprecated API before hybrid touches the file |
| V2–V3 | Zero user-facing change; builds the gate for V5 |
| V4 | Without names in indexed text, BM25 under-delivers on “Tiger Hill” / typos |
| V5 | The retrieval win — only after harness + reindex proof |
| V6 | Optional; do not pre-build cross-encoder |

---

## Environment Variables (v7 additions)

All via `get_settings()`. Defaults preserve today's behavior where possible.

| Var | Default | Role / fallback |
|-----|---------|-----------------|
| `QDRANT_PLACES_COLLECTION` | `places` | Legacy; prefer accessor reading V2 when cut over |
| `QDRANT_PLACES_COLLECTION_V2` | `places_v2` | Named dense+sparse collection |
| `SEARCH_SPARSE_ENABLED` | `true` (after V5) | Kill-switch → dense-only prefetch (v6.1-equivalent path) |
| `SEARCH_RRF_K` | `60` | RRF constant; no magic numbers in code |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | `""` | Empty → `NoOpTracer`, zero network |
| `PLACES_EMBEDDING_DIM` | `384` (or prod `768`) | Must match backend; V5 recreate if dim changes |
| Existing `QDRANT_*`, `LLM_*`, `PLANNER_*` | unchanged | — |

**Single accessor rule (mandatory at V5):** one function e.g. `places_collection() -> str` used by `ensure_places_collection`, upsert, `search_places`, `count_indexed`. Rollback = flip env that accessor reads — no split-brain.

---

## Resilience Contracts (v7 delta)

| Component | Retry | Timeouts | Final Fallback |
|-----------|-------|----------|----------------|
| `search/sparse.py` | none (CPU) | N/A | `is_sparse_available()=False` → dense-only |
| Hybrid `query_points` | tenacity 2× (existing) | `QDRANT_OPERATION_TIMEOUT_SECONDS` | `[]` → planner PostGIS geo fallback (unchanged) |
| Collection cutover | n/a | n/a | Keep old `places` until validated; flip accessor back |
| Usage capture | none | n/a | Empty `LLMUsage`; never raise |
| Tracer / Langfuse | none | SDK batching | Swallow + log-once; generation unaffected |
| Eval runner vs LLM | existing gateway | `PLANNER_GENERATION_TIMEOUT_SECONDS` | Score deterministic assertions only |
| CI | n/a | job timeout | Red PR; no deploy (Phase A has no deploy) |

Never retry Qdrant 4xx (config bugs). Observability is **never** on the critical path.

---

## Degradation ladders (max fail-soft)

### Search (after V5)

```
query
  ├─ sparse OK + dense OK  → prefetch both → RRF → hits
  ├─ sparse OFF/unavailable → dense-only prefetch (≈ v6.1)
  ├─ dense empty / Qdrant down → [] from search_places
  └─ planner tool            → PostGIS radius (used_geo_fallback=True)
       └─ no base coords     → empty_candidates (ok=True, soft)
```

### Observability (after V2)

```
generate()
  ├─ LANGFUSE keys set     → real tracer (fail-soft on errors)
  └─ keys empty (default)  → NoOpTracer — byte-identical to today
usage missing from provider → empty token_usage written; row still saved
```

### Cutover (V5)

```
1. ensure places_v2 (named vectors) — never raises
2. index_places → v2 (idempotent point ids)
3. harness + manual queries green
4. flip places_collection() to v2
5. keep old places until soak; then delete
Rollback: flip accessor / SEARCH_SPARSE_ENABLED=false
```

---

## Failure Boundary Summary (v7 delta)

| Failure | Response |
|---------|----------|
| Sparse encoder raises | Log once, mark unavailable, dense-only. App serves. |
| V2 collection missing at boot | `ensure_places_collection()` creates it; never raises |
| Partial points missing `bm25` | RRF still runs; fewer sparse candidates |
| Empty V2 before reindex | Search `[]` → **geo fallback** (not 500). Do not flip traffic until indexed |
| Langfuse/SDK error | Swallow + log-once; itinerary unaffected |
| Usage absent | Empty usage; evaluation row still written |
| Golden case regresses | Harness exit non-zero; block V5 cutover |
| Rollback needed | Env flip or revert commit; no migrations for V0–V5 |

v6.1 failure table in `docs/blueprint_final.md` still applies in full.

---

## Package decisions (locked defaults)

| Topic | Choice | Revisit when |
|-------|--------|--------------|
| BM25 encoder | Pure-Python in `src/search/sparse.py` | Evals show BM25 recall weak **and** image cost accepted **and** vocab miss is dominant |
| `rank-bm25` / `fastembed` | Rejected / deferred | See `docs/next_version.md` |
| Eval harness | Hand-rolled `scripts/run_evals.py` | Only if LLM-as-judge added |
| Langfuse | Keep `langfuse==2.60.10` (v2 API) | Do **not** upgrade to v3 (removed `trace()`) |
| New packages | None for default V0–V5 | requirements.txt + why-comment first |

---

## Phase Blueprint

### Legend
- 📦 Package installed at this step (prefer **none** for v7)
- 🏗️ LLD pattern
- 🚨 Failure boundary / fallback
- ☁️ Production consideration
- 🔒 Resilience contract applied
- ✅ Ship proof

---

### V0 — Minimal CI
**~0.5 day · gate for everything below**  
**Detail:** `docs/ci_cd_plan.md` Phase A

#### V0.1 GitHub Actions `ci.yml`
- Jobs: `pytest tests/ -v`; `docker build -f Dockerfile .`
- Triggers: push/PR to `main`
- No secrets; no live Postgres/Qdrant required (suite is mocked)
- 🚨 CI red → do not merge V1+
- ☁️ No deploy, no registry push
- ✅ Workflow file exists; green on main

#### V0.2 (optional later) Wire golden harness job
- Only after V3 lands: add `scripts/run_evals.py` job
- ✅ Documented hook in ci_cd_plan; not blocking V1–V2

**Non-goal:** Phase B full CD — deferred until deploy pain.

---

### V1 — Deprecation-proof query path (zero behavior change)
**~0.5 day · `src/search/places_index.py` + tests**

#### V1.1 Migrate `client.search` → `client.query_points`
- Same filter, limit, destination_id match
- Map `QueryResponse.points[]` → `PlaceSearchResult` (payload/score)
- 🏗️ Adapter over Qdrant client API
- 🚨 Qdrant errors → `[]` (unchanged)
- 🔒 Existing tenacity + `QDRANT_OPERATION_TIMEOUT_SECONDS`
- ✅ Manual: same top-k ordering snapshot for one Darjeeling query

#### V1.2 Update **three** pinned tests (not one)
- `test_search_places_includes_destination_filter`
- `test_search_places_returns_empty_on_qdrant_error`
- `test_search_places_short_circuits_on_empty_embedding`
- Mock `query_points` instead of `search`
- ✅ `pytest tests/search -v` green

**OpenSpec:** fold into hybrid change tasks when implementing.

---

### V2 — Observability (token, retry, Langfuse)
**~2–3 days · fail-soft · keys empty = NoOp**  
**OpenSpec:** `wire-langfuse-tracing-and-eval-harness` Stages 1–3

#### V2.1 Honest usage + retry in `core/llm/client.py`
- `LLMUsage` dataclass; capture `response.usage` in `chat_completion` / `chat_with_tools` / `embed_texts`
- Missing usage → empty, never raise
- Count retries via existing `_llm_retry` / `before_sleep`
- 🏗️ Gateway Pattern (unchanged entrypoint)
- 🚨 Provider omits usage → empty totals
- ✅ Return contracts compatible with callers; `pytest tests/core -v`

#### V2.2 Thread into TravelState + evaluation
- **Add** `token_usage` to `TravelState` (not present today); seed `{}` in `_initial_state()`
- Accumulate usage; replace crude `llm_retry_count + 1` on `WandrLLMError` in agent / parse_preferences / write_narrative with honest counts (avoid double-count)
- `EvaluationService.record_generation` already maps keys — **no migration**
- 🚨 Evaluation write still fail-soft
- ✅ Generate once → `trip_evaluations` row has real token totals

#### V2.3 Wire Langfuse at `PlannerService.generate`
- Trace start/end including timeout/abort paths
- Generation spans from gateway; tool spans post-hoc from `tool_trace` (no tool code changes)
- Empty keys → `NoOpTracer`
- Note: `flush_tracer()` **already** called in `main.py` lifespan shutdown — do not document as “unused”
- Keep `langfuse==2.60.10`
- 🚨 Tracer exception → swallow + log-once; generation succeeds
- ✅ Keys unset → identical results, no traffic; keys set → one trace per generate

---

### V3 — Golden-dataset regression harness
**~2 days · offline · never exact LLM string match**  
**OpenSpec:** same change, Stage 4

#### V3.1 Case schema + Darjeeling golden set
```
evals/golden/darjeeling/*.json
evals/baselines/<dest>.json
evals/runs/<ts>-<sha>.json
```
- Assertions: `must_include_places`, `validation_passed`, `max_days`, `no_geo_fallback`, readiness/tool bounds — **never** exact narrative strings
- 🏗️ Property-based evaluation
- ✅ Cases validate on load; bad case names fail fast

#### V3.2 Pure scorers + runner
- `src/evaluation/scorers.py` — feasibility delegates to `trip_validator.validate_trip`
- `scripts/run_evals.py` — `PlannerService.generate(routing=FakeRoutingProvider...)`
- Baseline diff; `--update-baseline` explicit; exit non-zero on regression
- LLM-unavailable mode still scores deterministic assertions
- 🚨 LLM down → deterministic subset still scored
- ✅ Fresh baseline exit 0; broken expectation → named non-zero diff

---

### V4 — Expand canonical text for sparse (and dense)
**~0.5 day · zero new deps · before RRF**

#### V4.1 Include `name` (± `category`) in `_canonical_text`
- Today: `summary + enriched_tags` only — names sit in payload but not vectors
- Target: BM25 (and dense) see exact place tokens (“Tiger Hill”, category hints)
- Keep enriched_tags; never raw OSM `tags` for embed text (existing rule)
- 🚨 Empty name → omit gracefully
- ✅ Re-embed/reindex one destination; spot-check name query hits improve vs pre-snapshot
- ☁️ Requires reindex for affected destinations before relying on V5

**Why before V5:** hybrid without name tokens under-delivers on the stated vocabulary-mismatch why.

---

### V5 — Hybrid dense + sparse + RRF (`places_v2`)
**~2–3 days · harness-gated · dual collection**  
**OpenSpec:** `hybrid-dense-sparse-place-search`

#### V5.1 Settings + `places_collection()` accessor
- Add `QDRANT_PLACES_COLLECTION_V2`, `SEARCH_SPARSE_ENABLED`, `SEARCH_RRF_K`
- Route **all four** collection references through one accessor
- 🚨 Misconfig → fail-soft ensure; never crash boot
- ✅ Unit/settings tests; accessor single source of truth

#### V5.2 `src/search/sparse.py`
- `is_sparse_available()`, `encode_sparse`, `encode_sparse_batch`
- Pure-Python tokenize + term weights; query-side without corpus IDF OK for MVP
- 🚨 Encode failure → unavailable → dense-only
- ✅ Unit tests; no new packages

#### V5.3 Collection ensure with named vectors
```
vectors_config: { "dense": VectorParams(size=PLACES_EMBEDDING_DIM, COSINE) }
sparse_vectors_config: { "bm25": SparseVectorParams() }
```
- Create `places_v2` only; do not break existing `places`
- 🏗️ Expand/contract collection migration
- ✅ Boot with Qdrant down still fail-soft (`is_qdrant_available=False`)

#### V5.4 Index path — conditional named vectors
- Upsert `vector={"dense": ..., "bm25": ...}` conditionally; skip point only if dict empty
- bm25-only points invisible to dense-only degradation — documented fail-soft, not a bug
- One batch `upsert` call (pinned test)
- ✅ `index_places --destination Darjeeling` → count matches Qdrant

#### V5.5 Query path — server-side RRF
- `query_points` with dual `Prefetch` + `FusionQuery(RRF)`
- Sparse off/unavailable → dense-only prefetch
- 🚨 Qdrant fail → `[]` → geo fallback in planner tool (unchanged)
- ✅ Harness: `must_include_places` / `no_geo_fallback` green; typo/name queries top-5; `SEARCH_SPARSE_ENABLED=false` ≈ V1 dense behavior

#### V5.6 Cutover checklist
1. Index complete for target destinations  
2. Harness green against v2  
3. Flip accessor to v2  
4. Soak; retain old collection  
5. Delete old only after soak  
- 🚨 Never flip to empty v2 in prod  
- ✅ Rollback drill: flip env → dense path healthy under CI

---

### V6 — Evidence-driven polish (conditional)
**Only if** `TripEvaluation.tool_trace` / harness show retrieval misses dominant

#### V6.1 Fusion diagnostics in tool_trace (optional)
- Dense vs sparse vs fused order — fail-soft logging only

#### V6.2 Embedding model bump (optional)
- e.g. `bge-small-en-v1.5` if still 384d — reindex-only; dim change needs new collection

#### V6.3 Cross-encoder rerank (NOT pre-approved)
- New decision required; not part of default v7

---

## Guardrail compliance checklist (every V-step)

- [ ] Changes confined to allowed modules for that step (`src/search/`, `src/config.py`, `src/core/llm/`, `src/core/observability/`, `src/planner/`, `src/evaluation/`, `evals/`, `scripts/`, tests, docs)
- [ ] No litellm/langfuse imports outside gateway / tracing facade
- [ ] No new packages without requirements.txt + why-comment
- [ ] All env via `get_settings()`
- [ ] Fail-soft preserved; tool `candidate_pois` contract unchanged
- [ ] `pytest` green for touched suites; V5 also harness green
- [ ] Update `docs/context.md` when a V-step is validated (Last updated / Next step / Implemented modules)

---

## Timeline Summary

| Phase | Effort | Focus | User-facing break risk |
|-------|--------|-------|------------------------|
| V0 | 0.5d | CI gate | None |
| V1 | 0.5d | `query_points` | None |
| V2 | 2–3d | Tokens + Langfuse | None (NoOp default) |
| V3 | 2d | Golden harness | None (offline) |
| V4 | 0.5d | Canonical text | None until reindex (then better hits) |
| V5 | 2–3d | Hybrid RRF | **Ranking may change**; APIs unchanged |
| V6 | TBD | Polish | Evidence-only |
| CD B | TBD | Auto-deploy | Ops only |

---

## Quick Reference: What v7 may and may not change

| May change | Must not change |
|------------|-----------------|
| Qdrant ranking / fusion internals | HTTP paths, DTO envelopes, SSE event names |
| `TravelState` internal fields (`token_usage`) | `travel_engine` purity / I/O rules |
| Evaluation column *values* (honesty) | Evaluation column *schema* (no migration for V2) |
| Which POIs win for a query | Geo fallback existence; generate floor 409 rules |
| Ops: collection name via env | Requirement that empty Langfuse keys still boot |

---

## Relationship to other docs

| Doc | Role |
|-----|------|
| `docs/blueprint_final.md` | P0–P7 SSOT (unchanged) |
| **`docs/v2_blueprint.md`** | **Post-P7 build SSOT (this file)** |
| `docs/next_version.md` | Package decisions + detailed why tables |
| `docs/ci_cd_plan.md` | CI/CD phases |
| `docs/context.md` | Agent checkpoint after each validated step |
| `AGENT.md` | Hard coding guardrails |

---

## Production hardening (deferred — non-blocking)

- Full CD Phase B (`docs/ci_cd_plan.md`)
- fastembed sparse if pure-Python BM25 underperforms
- Cross-encoder / LLM-as-judge
- Deleting legacy `places` collection (only after soak)
