## 1. Step 2.7b — Places HTTP router

- [x] 1.1 Implement `src/places/router.py`: `APIRouter(prefix="/api/v1/places", tags=["places"])`; `GET ""` list via `PlaceService.list_by_destination` + `paginate`; `GET /{place_id}` via `PlaceService.get_by_id` → `ApiResponse[PlaceOut]` (Router → Service only)
- [x] 1.2 Register places router in `src/main.py` (`include_router`)
- [x] 1.3 Prerequisite: seeded Darjeeling (`python scripts/seed_destination.py --destination "Darjeeling" --radius 30` if needed); resolve `DESTINATION_ID` / `PLACE_ID`
- [x] 1.4 Validate list: `curl .../api/v1/places?destination_id={DESTINATION_ID}&page=2&size=10` → `total>=50`, `page=2`, `pages>=5`, `has_next=true`, 10 items
- [x] 1.5 Validate get + failure paths: existing place 200; unknown place UUID → 404; unknown `destination_id` on list → 404 `not_found` (not empty page)

## 2. Step 2.8 — Readiness scoring

- [x] 2.1 Implement `src/destinations/readiness.py`: `PLACE_TARGET`, frozen `ReadinessResult`, pure `compute_readiness` (locked formula + messages); zero SQLAlchemy/FastAPI/httpx/qdrant imports
- [x] 2.2 Replace stub `DestinationService.get_readiness`: load dest → `search_available=False` → `compute_readiness` → `DestinationReadinessOut`
- [x] 2.3 Unit-validate math (step 2.8 python -c): `(144,0,0,False)` → limited / score 0.35–0.45; `(144,100,100,True)` → ready / score ≥ 0.7
- [x] 2.4 Validate HTTP: seeded readiness → limited band, `enriched_pct`/`indexed_pct` 0.0; unknown destination UUID → 404

## 3. Context checkpoint

- [x] 3.1 Update `docs/context.md`: 2.7b + 2.8 ✅, Next → **2.9**, Implemented modules (`places/router`, `destinations/readiness`, real `get_readiness`), Live endpoints (places list/get; readiness no longer stub), stubs note (remove places router + readiness interim stub)
