## 1. Settings and search sidecar

- [x] 1.1 Add `SEARCH_FUSION_DIAGNOSTICS: bool = True` via `get_settings()` (document in `.env.example` if present); kill-switch false skips diagnostic queries
- [x] 1.2 In `src/search/places_index.py`, attach fusion diagnostics sidecar on search (mode, collection, sparse_enabled, fused/dense/sparse place_id lists, top_k) without changing primary hit order; hybrid path may run extra dense/sparse queries only when flag on
- [x] 1.3 Fail-soft: diagnostic subquery errors leave primary hits intact; dense-only / unavailable modes still emit a partial diagnostics object when flag on
- [x] 1.4 Unit tests: hybrid + dense-only diagnostics shapes; diagnostic failure does not empty results; flag false skips extras (`pytest tests/search -v`)

## 2. Planner tool_trace wiring

- [x] 2.1 Add optional `diagnostics` field on `ToolTraceEntry` (backward compatible)
- [x] 2.2 `search_places` tool: put search sidecar in `ToolResult.data["fusion_diagnostics"]`; keep `candidate_pois` / `used_geo_fallback` semantics unchanged
- [x] 2.3 `apply_tool_result`: copy `fusion_diagnostics` onto the trace entry; do **not** add it to `_MERGE_KEYS`
- [x] 2.4 Unit/orchestration tests: diagnostics appear on `tool_trace` for search_places; missing diagnostics still appends entry; TravelState does not gain a `fusion_diagnostics` planning field (`pytest tests/planner -v` or targeted tool tests)

## 3. Proof and docs

- [x] 3.1 Guardrail check: no new packages; all env via `get_settings()`; HTTP/SSE/`candidate_pois` contract unchanged; `_format_tool_trace` does not dump full diagnostics into the LLM prompt
- [x] 3.2 Optional smoke: unit proof of search → `ToolResult.data` → `tool_trace.diagnostics` path (live Darjeeling generate optional when stack up)
- [x] 3.3 Update `docs/context.md` (Last updated, Next step, Progress V6.1 ✅, note V6.2/V6.3 still deferred pending evidence)
