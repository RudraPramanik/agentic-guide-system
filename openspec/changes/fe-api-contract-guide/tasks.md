## 1. Guide structure & source-of-truth

- [x] 1.1 Re-read live routers + `src/*/schemas.py` + `docs/context.md` Live endpoints before editing (do not expand from memory)
- [x] 1.2 Add a short “API contract / source of truth” preamble in `docs/FE_guide.md` (schemas + `/docs` win; FE_guide is FE-oriented mirror; update when routes/DTOs change)
- [x] 1.3 Keep existing stack/env/auth/SSE high-level sections; extend rather than rewrite locked MVP tables

## 2. Auth matrix & domain route map

- [x] 2.1 Expand §8 (or successor) endpoint tables with Auth + ownership notes for every live MVP route
- [x] 2.2 Call out envelope exceptions: bare `PaginatedResponse` (places/trips list), raw GeoJSON, SSE, DELETE 204
- [x] 2.3 Note evaluation HTTP remains stub — do not add FE modules for it

## 3. DTO sketches & readiness fix

- [x] 3.1 Add TypeScript-oriented DTO sketches: envelopes, auth me/user, destinations, places, `PlanRequest`, trips + edit bodies, pagination query defaults
- [x] 3.2 Fix readiness UX (`tier`/`score`/pcts/`message`) — remove implied returned `search_available` field
- [x] 3.3 Label sketches as mirrors of Python schemas (schemas win on conflict)

## 4. SSE, GeoJSON, errors, rate limits

- [x] 4.1 Expand planner SSE section with progress vs terminal event catalog and representative `data` keys; note cache replay omits tool events; prefer `trip_id` → GET trip
- [x] 4.2 Document GeoJSON Point/LineString properties and `[lng, lat]` coordinates for MapLibre
- [x] 4.3 Add FE-relevant error `code` catalog + SSE error codes; summarize UX-visible rate-limited routes (use numbers already in context.md where published)

## 5. Cross-links & verify

- [x] 5.1 Optional: one-line pointer from `docs/context.md` Live endpoints → `docs/FE_guide.md` API contract (no progress-table churn)
- [x] 5.2 Spot-check guide tables against routers/schemas one final time; confirm no invented endpoints or fields
- [x] 5.3 Confirm non-goals still hold: no FastAPI code changes, no FE scaffold in this change
