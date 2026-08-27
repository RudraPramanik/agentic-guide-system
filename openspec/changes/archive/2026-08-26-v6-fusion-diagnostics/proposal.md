## Why

V0–V5 are done (hybrid RRF on `places_v2`), but generate-mode golden runs still mix retrieval-ish failures (`used_geo_fallback`, missing Tiger Hill) with planner failures (day bounds, tool-call caps). Blueprint V6 is evidence-gated: we need per-query dense vs sparse vs fused visibility in `tool_trace` before any embedding bump or cross-encoder. Without diagnostics, we cannot tell empty-index / kill-switch / ranking miss apart — and must not “polish” ranking blind.

## What Changes

- **V6.1 only:** Emit fail-soft **fusion diagnostics** for place search into `tool_trace` (dense top ids, sparse top ids, fused top ids/scores, mode, collection, sparse on/off).
- Search ranking path for candidates **unchanged**: diagnostics MUST NOT alter returned `PlaceSearchResult` order or geo-fallback ladder.
- Optional settings kill-switch (e.g. `SEARCH_FUSION_DIAGNOSTICS`, default on or off per design) so ops can disable extra diagnostic queries without code rollback.
- Wire diagnostics through `search_places` tool → `ToolResult.data` → `ToolTraceEntry` (optional field); do **not** merge diagnostics into TravelState planning keys (`candidate_pois` contract unchanged).
- Unit tests for payload shape + fail-soft (diagnostic error never empties search hits).
- Update `docs/context.md` when validated; cite `docs/v2_blueprint.md` V6.1.

**Non-goals / deferred:** V6.2 embedding model bump; V6.3 cross-encoder; fastembed; changing RRF `k` as a “fix”; HTTP/SSE/OpenAPI/FE changes; fixing planner day-count / max_tool_calls golden failures (separate from V6); closing hybrid task 6.2 harness ops work (recommended parallel triage, not this change’s code scope).

## Capabilities

### New Capabilities
- `search-fusion-diagnostics`: Per-query hybrid search diagnostics (mode + dense/sparse/fused id lists) recorded for evaluation/debug without changing retrieval results used for planning.

### Modified Capabilities
- `hybrid-dense-sparse-search`: Hybrid/dense search path MAY attach a diagnostics sidecar; result list contract and fail-soft `[]` behavior MUST remain unchanged.
- `planner-discover-tools`: `search_places` MUST forward diagnostics into `ToolResult.data` without changing `candidate_pois` / `used_geo_fallback` semantics.
- `planner-tool-registry`: `ToolTraceEntry` MAY carry optional diagnostics; `apply_tool_result` MUST copy them into the trace entry and MUST NOT treat them as TravelState merge keys.

## Impact

- **Code:** `src/search/places_index.py` (optional diagnostic prefetches/sidecar); `src/planner/tools/search_places.py`; `src/planner/tools/schemas.py` (`ToolTraceEntry`); `src/planner/tools/orchestration.py` (`apply_tool_result`); `src/config.py` if a settings flag is added; tests under `tests/search/` and `tests/planner/`.
- **APIs / FE:** None — HTTP, SSE, trip DTOs unchanged. Evaluation JSON may gain richer `tool_trace` entries (additive, fail-soft).
- **Deps:** None.
- **Ops:** Optional env for diagnostics on/off; no collection migration; no reindex required for this step alone.
- **AGENT.md:** All env via `get_settings()`; no new packages; fail-soft preserved; LLM still gateway-only.
- **Docs:** `docs/context.md` after validation; SSOT step = `docs/v2_blueprint.md` V6.1.
