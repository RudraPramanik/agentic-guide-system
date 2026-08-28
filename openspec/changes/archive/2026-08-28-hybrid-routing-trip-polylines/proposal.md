## Why

Trip maps show stop markers but almost never road routes because default `ROUTING_BACKEND=haversine` makes `route_polyline` always return `None`, so GeoJSON stays Point-only. We need Layla-like (or simpler) day polylines without putting full OSRM pairwise matrices on the generate hot path (45s budget / public OSRM risk).

## What Changes

- Add a **hybrid** routing adapter (or equivalent factory mode): `travel_matrix` stays in-process haversine; `route_polyline` uses live OSRM via `geo/osrm.get_route` (fail-soft → `None`).
- Extend `ROUTING_BACKEND` / `get_routing_provider()` so default production generate stays fast while geometry can be populated after stop order is fixed (`populate_leg_polylines` path unchanged).
- Document operator env (`.env.example` / `docs/context.md`): hybrid vs `haversine` vs full `osrm`; note existing trips need regenerate or day reoptimize to gain lines.
- Cross-link sibling frontend change `trip-route-polyline-map` and parent vault change `cross-trip-route-polylines` (no FE code in this remote).

### Non-goals

- Self-hosted OSRM / docker-compose routing service
- Changing GeoJSON envelope, inventing crow-flies in `build_geojson`, or network I/O inside `build_geojson`
- Frontend MapLibre styling (day colors, numbered badges) — FE remote
- Defaulting all environments to full `ROUTING_BACKEND=osrm` matrix mode
- Backfill job for historical trips

## Capabilities

### New Capabilities

- `hybrid-routing-provider`: Hybrid `RoutingProvider` — haversine matrix + OSRM polylines; factory selection via settings

### Modified Capabilities

- `planner-routing-provider`: `get_routing_provider` / `ROUTING_BACKEND` must select hybrid (in addition to haversine | osrm)
- `route-geometry-polyline`: Clarify that default generate path can persist non-null polylines when hybrid (or osrm) geometry succeeds; Point-only degrade unchanged when polyline is `None`

## Impact

- **Code:** `src/planner/routing_provider.py`, `src/config.py` (`ROUTING_BACKEND` values), tests under `tests/planner/`; docs `docs/context.md`, `.env.example` if present
- **APIs:** No new endpoints; `GET /trips/{id}/geojson` may gain LineStrings for newly generated/edited trips
- **AGENT.md:** Geo only via `src/geo/`; settings via `get_settings()`; fail-soft polylines
- **Siblings:** `guideagent-frontend` change `trip-route-polyline-map`; parent `cross-trip-route-polylines`
- **Constraints:** Do not call OSRM outside `geo/`; do not put HTTP in `travel_engine/`
