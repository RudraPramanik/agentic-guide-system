## Context

P2.7a is done: `PlaceService` / `PlaceOut` exist; destinations search + readiness **route** are live, but `get_readiness` still returns an interim stub. Canonical next pair from `docs/steps/step2.md`: **2.7b** (places HTTP) then **2.8** (pure readiness + real service). No new external I/O — both are thin router/service/pure-math layers over existing repositories and denormalized destination counters.

## Goals / Non-Goals

**Goals:**
- Mount `GET /api/v1/places` and `GET /api/v1/places/{place_id}` via `PlaceService` only; return `PaginatedResponse[PlaceOut]` / `ApiResponse[PlaceOut]`
- Unknown place → 404; unknown destination on list → 404 `not_found` (never empty page)
- Implement locked P2 `compute_readiness` as a pure function; wire `DestinationService.get_readiness` to it with `search_available=False`
- Seeded Darjeeling readiness → `tier=limited`, score in ≈0.35–0.45 band; unknown destination readiness → 404
- Update `docs/context.md` → Next **2.9**

**Non-Goals:**
- 2.9 pytest modules / 2.10 smoke script
- Developer-manual refresh (cadence doc; separate change)
- Calling Qdrant or flipping `search_available` (P3)
- Changing places service existence-check semantics (already locked in 2.7a)
- Rate-limit changes for places endpoints

## Decisions

### D1 — Places router mirrors destinations thin pattern
- `APIRouter(prefix="/api/v1/places")`; `list_places` takes `destination_id: uuid.UUID` query + `PageParams` + `get_db`; calls `PlaceService.list_by_destination` then `paginate(...)`
- `get_place` returns `ApiResponse(data=await PlaceService(...).get_by_id(...))`
- Alternative considered: nest places under `/destinations/{id}/places` — rejected; step 2.7b locks flat `/places` with `destination_id` query

### D2 — Register places router in `create_app` beside destinations
- `from src.places.router import router as places_router` + `app.include_router(places_router)`
- No middleware or exception-handler changes needed (`WandrError` / `DestinationNotFoundError` / `NotFoundError` already mapped)

### D3 — Pure readiness module with zero I/O imports
- `src/destinations/readiness.py`: `PLACE_TARGET = 100`, frozen `ReadinessResult` dataclass, `compute_readiness(place_count, enriched_count, indexed_count, search_available)`
- Formula (locked in step2.md):
  - `place_score = min(place_count / PLACE_TARGET, 1.0)`
  - `enriched_pct = enriched_count / place_count if place_count > 0 else 0.0`
  - `indexed_pct = (indexed_count / place_count) if (place_count > 0 and search_available) else 0.0`
  - `score = round(0.4 * place_score + 0.35 * enriched_pct + 0.25 * indexed_pct, 3)`
  - `tier = "ready" if score >= 0.7 else "limited" if score >= 0.3 else "sparse"`
- Messages: sparse → `"Very limited POI data — results may be generic"`; limited when `enriched_pct < 0.5` → `"Limited enrichment — semantic search not yet available"`; ready → `None`
- MUST NOT import SQLAlchemy, FastAPI, httpx, or qdrant
- Alternative considered: compute inside service method — rejected; step locks a dedicated pure module for unit-testability

### D4 — Service always passes `search_available=False` in P2
- Load destination via existing `get_by_id` (raises `DestinationNotFoundError`)
- Call `compute_readiness(dest.place_count, dest.enriched_count, dest.indexed_count, False)`
- Map into `DestinationReadinessOut` (destination_id + result fields)
- Endpoint stays 200 even when indexed/enriched are zero — never fail because Qdrant is “unavailable”
- Alternative considered: probe Qdrant health for `search_available` — rejected; P2 rule is hard False until P3

### D5 — Bundle order in implementation
- Land 2.7b (router + main registration) and validate list/get + both 404 paths with seeded data
- Then 2.8 (readiness.py + service) and validate curl + inline `compute_readiness` asserts
- Context bump only after both gates pass

## Risks / Trade-offs

- **[Risk]** Validation needs seeded Darjeeling (`place_count >= 50`) → **Mitigation:** tasks list seed prerequisite; fail clearly if empty
- **[Risk]** Message rules for `limited` when `enriched_pct >= 0.5` are underspecified in step text → **Mitigation:** apply limited message only when `enriched_pct < 0.5`; otherwise `message=None` for limited/ready; sparse always gets sparse message
- **[Risk]** Blueprint “tier=ready after seed” vs formula (`ready` needs enrichment) → **Mitigation:** follow step2 locked amendment — P2 acceptance is `tier=limited`
- **[Trade-off]** Bundling 2.7b+2.8 skips shipping places HTTP alone → acceptable; readiness is small and destinations route already calls `get_readiness`

## Migration Plan

- No DB migration; additive Python modules + router registration
- Deploy: restart uvicorn
- Rollback: remove places router include; restore stub `get_readiness` / delete `readiness.py`

## Open Questions

- None blocking. Optional later: path-specific rate limit for `/places` list (not in step2; leave default 60/min).
