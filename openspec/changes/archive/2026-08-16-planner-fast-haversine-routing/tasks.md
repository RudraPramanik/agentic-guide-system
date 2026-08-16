## 1. Settings and geo helper

- [x] 1.1 Add `ROUTING_BACKEND: str = "haversine"` to `src/config.py` (via `get_settings()` only)
- [x] 1.2 Document `ROUTING_BACKEND=haversine` (and `osrm` + existing `OSRM_BASE_URL`) in `.env.example`
- [x] 1.3 Export public `estimate_route` in `src/geo/osrm.py` (haversine × 1.4 / 30 km/h, `fallback_used=True`, no HTTP); reuse it from `get_route` miss path; `<2` waypoints → `ValueError`

## 2. Provider factory

- [x] 2.1 Add `HaversineRoutingProvider` in `src/planner/routing_provider.py`: pairwise `estimate_route` legs with `used_fallback=True`; `route_polyline` always `None`; no `get_route`
- [x] 2.2 Add `get_routing_provider()` selecting haversine vs `OsrmRoutingProvider` from `ROUTING_BACKEND` (unknown → haversine)
- [x] 2.3 Default `PlannerService.generate` ToolContext routing to `get_routing_provider()` when caller does not inject
- [x] 2.4 Default `TripService` routing to `get_routing_provider()` when constructor has no `routing=` override
- [x] 2.5 Confirm `travel_engine/` still has zero geo imports

## 3. Tests

- [x] 3.1 Unit test `estimate_route`: positive distance, `fallback_used=True`, no httpx; `<2` waypoints raises
- [x] 3.2 Unit test `HaversineRoutingProvider`: 3 waypoints → 6 fallback legs; `route_polyline` is `None`
- [x] 3.3 Unit test factory: default / unknown → haversine (no `get_route`); `ROUTING_BACKEND=osrm` → `OsrmRoutingProvider`
- [x] 3.4 Assert generate and TripService defaults use the factory (or equivalent source/behavior check)
- [x] 3.5 Run `python -m pytest tests/planner/ tests/geo/ tests/trips/ tests/travel_engine/ -q` and confirm green

## 4. Proof and docs

- [x] 4.1 Live (or instrumented) Darjeeling `POST /api/v1/planner/generate` with default 45s ceiling → terminal `itinerary_done` + `trip_id` (Point-only GeoJSON OK)
- [x] 4.2 Update `docs/context.md` (Last updated, implemented-modules note for routing factory / `ROUTING_BACKEND`, drop any claim that public OSRM is required for cold generate under 45s)
