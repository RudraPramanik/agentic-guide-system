## 1. Step 2.5 — OSRM gateway

- [x] 1.1 Replace stub `src/geo/osrm.py` with `_haversine_km`, `_fallback_route`, `_call_osrm` (tenacity 2x, Timeout/ConnectError only), and public `get_route` → `RouteResult` (URL lng,lat; settings.OSRM_BASE_URL; explicit httpx timeouts)
- [x] 1.2 Validate live: `python -c` get_route Darjeeling pair → `distance_km > 0` + PASS (PYTHONPATH=repo root)
- [x] 1.3 Validate failure path: mock `_call_osrm` → None → `fallback_used=True` and `distance_km > 0`

## 2. Step 2.6c — Destinations HTTP

- [x] 2.1 Implement `src/destinations/router.py`: `GET /search` → DestinationService.search → `ApiResponse[list[DestinationOut]]`; `GET /{id}/readiness` → get_readiness; no geocode/repo imports in router
- [x] 2.2 Add thin `DestinationService.get_readiness` stub (404 if missing; interim DestinationReadinessOut + message until 2.8)
- [x] 2.3 Register destinations router in `src/main.py`

## 3. API + browser validation (see the result)

- [x] 3.1 Ensure Postgres up (`docker compose up -d`); start `uvicorn src.main:app --reload --port 8000`
- [x] 3.2 curl search: `http://localhost:8000/api/v1/destinations/search?q=Darjeeling` → JSON with ≥1 destination, lat/lng present
- [x] 3.3 curl failure: `q=XyzzyNonexistent999` → 404 `not_found`
- [x] 3.4 Browser: open `http://localhost:8000/docs` — confirm Destinations tag + Try it out on `/search` returns Darjeeling
- [x] 3.5 Browser: open `http://localhost:8000/api/v1/destinations/search?q=Darjeeling` directly — confirm raw JSON visible
- [x] 3.6 Optional smoke: readiness for seeded Darjeeling id returns 200 stub; random UUID → 404

## 4. Context checkpoint

- [x] 4.1 Update `docs/context.md`: 2.5 + 2.6c ✅, Next → **2.6c′**, Implemented modules (osrm + destinations router), Live endpoints table, stubs note (readiness scoring still 2.8; rate limit still 2.6c′)
