## 1. Hybrid provider + settings

- [x] 1.1 Extend `ROUTING_BACKEND` docs/validation in `src/config.py` to accept `hybrid` (unknown → haversine; default remains `haversine`)
- [x] 1.2 Implement hybrid adapter in `src/planner/routing_provider.py` (haversine `travel_matrix`, OSRM fail-soft `route_polyline` via `geo/osrm.get_route` only)
- [x] 1.3 Wire `get_routing_provider()` for `hybrid`; keep `haversine` / `osrm` behavior
- [x] 1.4 Add/extend `tests/planner/test_routing_provider.py` for hybrid matrix (no HTTP) + polyline success/None paths

## 2. Docs + operator notes

- [x] 2.1 Update `docs/context.md` known limitation: hybrid enables GeoJSON LineStrings; recommend `ROUTING_BACKEND=hybrid` for map routes; full `osrm` still optional/spike
- [x] 2.2 Update `.env.example` (if present) with commented `ROUTING_BACKEND=hybrid` and pointer to sibling FE change `trip-route-polyline-map`
- [x] 2.3 Note in context/FE_guide cross-ref: old trips need regenerate or day reoptimize; no GeoJSON schema change

## 3. Proof

- [x] 3.1 Run targeted pytest for routing provider (+ any polyline optimizer tests still green)
- [x] 3.2 Manual or scripted smoke with `ROUTING_BACKEND=hybrid`: generate or reoptimize → `GET /trips/{id}/geojson` includes LineString when OSRM succeeds; Point-only when soft-fail
- [x] 3.3 Confirm `build_geojson` still does no network I/O
