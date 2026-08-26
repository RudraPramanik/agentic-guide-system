## Context

V5 hybrid RRF is live behind `places_collection()` / `SEARCH_SPARSE_ENABLED`. Server-side `FusionQuery(RRF)` returns only the fused hit list — dense vs sparse contribution is invisible today (`places_index.search_places` + planner `search_places` tool). `ToolTraceEntry` records name/ok/ms/phase/code/fallback only; `apply_tool_result` merges a fixed `_MERGE_KEYS` set into TravelState and drops other `ToolResult.data` keys from the trace. See proposal.md for why V6.1 is diagnostics-only.

SSOT: `docs/v2_blueprint.md` V6.1; package decisions in `docs/next_version.md` Stage 3 (diagnostics first; embedding bump / cross-encoder deferred).

## Goals / Non-Goals

**Goals:**
- Record mode + fused (+ dense/sparse when hybrid) place_id orders into `tool_trace` for eval/debug.
- Zero change to candidate ranking used for planning when diagnostics succeed or fail.
- Settings kill-switch; no new packages; no HTTP/FE contract change.

**Non-Goals:**
- V6.2 embedding swap, V6.3 cross-encoder, changing `SEARCH_RRF_K` as a quality fix.
- Fixing planner golden failures (`max_days`, `max_tool_calls`) in this change.
- Putting diagnostics into Langfuse as a hard requirement (optional later; tool_trace is enough).

## Decisions

### 1. Sidecar return from search layer, not a second public API
**Choice:** Extend the search call path so the planner tool can obtain `(hits, diagnostics | None)` — e.g. optional out-param, small result wrapper, or internal helper used only by the tool — without changing the meaning of `list[PlaceSearchResult]` for other callers (`count_indexed` unchanged).
**Why:** Keeps Qdrant details in `src/search/`; tools stay thin.
**Alternatives:** Structlog-only (does not land in `TripEvaluation.tool_trace`); always-on triple query replacing fused results (would change ranking — rejected).

### 2. Extra dense/sparse queries only when diagnostics + hybrid RRF
**Choice:** Primary path remains today’s fused (or dense-only) `query_points`. When `SEARCH_FUSION_DIAGNOSTICS` is true and hybrid RRF is used, run additional dense-only and sparse-only queries (same filter, limit ≈ top_k) solely to capture id orders. On dense-only primary path, set mode `dense_only` and skip sparse subquery.
**Why:** Matches blueprint “dense vs sparse vs fused order”; FusionQuery alone cannot expose lists.
**Alternatives:** Fused-only diagnostics (cheaper, weaker evidence); always triple-query even when flag off (latency waste).

### 3. Settings: `SEARCH_FUSION_DIAGNOSTICS` default true
**Choice:** New bool on settings via `get_settings()`, default **true** so local generate/evals capture evidence after V5; set false to skip diagnostic queries (instant kill-switch).
**Why:** V6 is evidence-driven; default-on maximizes learning in this phase. Prod can flip off if latency matters.
**Alternatives:** Default false (safer latency, slower evidence); tie to `DEBUG` only (easy to miss in eval runs).

### 4. `ToolResult.data["fusion_diagnostics"]` → `ToolTraceEntry.diagnostics`
**Choice:** Add optional `diagnostics: dict[str, Any] | None = None` on `ToolTraceEntry`. `apply_tool_result` copies `data["fusion_diagnostics"]` onto the entry. Do **not** add `fusion_diagnostics` to `_MERGE_KEYS`.
**Why:** Persists into evaluation `tool_trace` JSON; avoids polluting TravelState / agent prompt merge fields; `_format_tool_trace` can ignore unknown keys safely.
**Alternatives:** Stuff into `message` (opaque); new TravelState field (unnecessary surface).

### 5. Payload shape (stable keys)
```
{
  "mode": "hybrid_rrf" | "dense_only" | "unavailable",
  "collection": "<name>",
  "sparse_enabled": bool,
  "fused_place_ids": ["..."],
  "dense_place_ids": ["..."],   # optional / empty if N/A or soft-fail
  "sparse_place_ids": ["..."],  # optional / empty if N/A or soft-fail
  "top_k": int
}
```
Scores optional in v1 (ids enough to bucket empty vs miss vs agent ignore).

### 6. Resilience
- Diagnostic queries: same `QDRANT_OPERATION_TIMEOUT_SECONDS`; no extra retry beyond existing patterns, or single attempt — prefer not doubling tenacity load.
- Any diagnostic exception: log once / debug, partial payload, **never** clear primary hits.
- Qdrant down: mode `unavailable`, empty id lists; existing geo fallback unchanged.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| +1–2 Qdrant RTTs when diagnostics on | Kill-switch; timeout shared; only on hybrid path for dense+sparse extras |
| Larger `tool_trace` / evaluation rows | Cap lists to top_k; omit scores if size becomes an issue |
| Agents see diagnostics in last-N tool_trace text | `_format_tool_trace` today uses name/ok/code — keep it that way; do not dump full diagnostics into LLM prompt |
| Hybrid change still has open harness 6.2 | Document as parallel ops triage; this change does not claim V5 harness closed |
| Misread geo_fallback as “BM25 bad” | Diagnostics + empty fused list vs non-empty clarifies ops vs ranking |

## Migration Plan

1. Ship code behind settings (default true).
2. No reindex, no collection flip, no FE deploy.
3. Rollback: `SEARCH_FUSION_DIAGNOSTICS=false` or revert commit; no DB migration.
4. After soak: use traces to decide whether V6.2 is warranted; do not auto-schedule embedding bump.

## Open Questions

None that block implementation. (Exact helper signature — wrapper vs tuple — left to apply-time preference as long as contracts hold.)
