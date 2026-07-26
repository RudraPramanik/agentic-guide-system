## 1. Step 2.6c′ — Destinations search rate limit

- [x] 1.1 Add to `src/config.py` + `.env.example`: `RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS=20`, `RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS=60`, `RATE_LIMIT_DESTINATIONS_SEARCH_PATH=/api/v1/destinations/search`
- [x] 1.2 Extend `src/core/middleware/rate_limit.py`: `_route_limit_table()` from settings; `_resolve_limits` exact-match table then default; keep fail-open
- [x] 1.3 Validate `_resolve_limits`: search → 20/60; planner → 10/60; `/api/v1/health` → default (step 2.6c′ python -c block)
- [x] 1.4 Run `python -m pytest tests/core/test_middleware.py -v` — must still pass
- [x] 1.5 Live (uvicorn up): curl search headers → `x-ratelimit-limit: 20`; optional 21st rapid request → 429

## 2. Step 2.7a — PlaceOut + PlaceService

- [x] 2.1 Implement `src/places/schemas.py`: `PlaceOut` + `from_place` via `geoalchemy2.shape.to_shape` (`.y`=lat, `.x`=lng)
- [x] 2.2 Implement `src/places/service.py`: `PlaceService` with PlaceRepository + DestinationRepository; `list_by_destination` (existence check → `DestinationNotFoundError` then paginate); `get_by_id` → PlaceOut
- [x] 2.3 Validate against seeded Darjeeling (step 2.7a python -c): `total >= 1`, non-zero lat; garbage UUID raises `DestinationNotFoundError` (seed first if needed)

## 3. Context checkpoint

- [x] 3.1 Update `docs/context.md`: 2.6c′ + 2.7a ✅, Next → **2.7b**, Implemented modules (rate-limit table + places schemas/service), stubs note (places router still stub until 2.7b)
