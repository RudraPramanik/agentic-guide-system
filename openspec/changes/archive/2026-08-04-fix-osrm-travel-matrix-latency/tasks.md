## 1. Settings

- [x] 1.1 Add `OSRM_MATRIX_MAX_CONCURRENCY: int = 8` to `src/config.py` Settings (via `get_settings()` only)
- [x] 1.2 Document `OSRM_MATRIX_MAX_CONCURRENCY=8` in `.env.example` with a short comment (public OSRM-safe default; tunable)

## 2. Provider implementation

- [x] 2.1 Rewrite `OsrmRoutingProvider.travel_matrix` to fan out all i≠j `get_route` calls under `asyncio.Semaphore(settings.OSRM_MATRIX_MAX_CONCURRENCY)` + `asyncio.gather` (preserve RouteLeg field mapping; empty list for fewer than 2 waypoints)
- [x] 2.2 Confirm `travel_engine/` still has zero geo imports and provider does not call httpx/OSRM except through `geo.osrm.get_route`

## 3. Tests

- [x] 3.1 Add unit test: mocked slow `get_route` + peak in-flight ≤ concurrency; assert full directed leg count for N waypoints
- [x] 3.2 Add/keep assertion that wall time for N≥4 is materially below serial `(n*(n-1))*delay` (same mock)
- [x] 3.3 Run `python -m pytest tests/planner/ tests/geo/ tests/travel_engine/ -q` (or project-equivalent routing-related paths) and confirm green

## 4. Live sanity (optional but recommended before P5.14 re-smoke)

- [x] 4.1 Time a 7-waypoint live `travel_matrix` against public OSRM; expect completion well under prior ~90s+ serial hang (document observed seconds in the apply session notes if useful)
- [x] 4.2 Do **not** stamp `docs/context.md` P5.14 here — after this change, resume `/opsx:apply ship-p5-14-smoke-nvidia-nim` for smoke + context ship
