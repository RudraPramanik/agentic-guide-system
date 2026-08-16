## Why

Darjeeling cold generate can finish, but public pairwise OSRM (`router.project-osrm.org`) makes `build_route` / `expand_poi_search` take minutes, so the graph hits `PLANNER_GENERATION_TIMEOUT_SECONDS` (45s) and the UI shows timeout instead of a trip. Self-hosting OSRM is not available now; a bigger LLM will not cut the first-pass matrix below 45s. MVP can ship a **minimal itinerary** (stops + times, no map lines) and keep the routing adapter ready for a paid OSRM later and a Layla-style guidebook on the same schedule.

## What Changes

- Add settings `ROUTING_BACKEND` (`haversine` | `osrm`), default **`haversine`**, via `get_settings()` only.
- Add `HaversineRoutingProvider` (same `RoutingProvider` protocol): in-process pairwise legs using existing geo haversine × 1.4 / 30 km/h; `route_polyline` always `None`; **no HTTP**.
- Export a public geo helper (never calls OSRM) so the haversine provider does not go through `get_route` (which still hits the public demo first).
- Add `get_routing_provider()` and use it as the default in `PlannerService.generate` and `TripService` (tests may still inject Fake).
- Leave `OsrmRoutingProvider` unchanged for later paid/self-host (`ROUTING_BACKEND=osrm` + `OSRM_BASE_URL`).
- Keep polyline fields on schedule / `TripPlace` (all `None` is already valid); GeoJSON stays Point-only until a live backend returns geometry.
- Proof: ready Darjeeling generate under the **default 45s** ceiling emits `itinerary_done` + `trip_id`.
- **Non-goals:** self-hosted OSRM, OSRM `/table`, paid Mapbox/Google, raising the 45s ceiling, FE abort/LLM-key changes, Layla PDF/guidebook/hotels/meals, rewriting the 12-tool graph, skipping polyline *code paths* in `travel_engine`.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `planner-routing-provider`: Add `HaversineRoutingProvider` + `get_routing_provider()` selected by `ROUTING_BACKEND`; keep `OsrmRoutingProvider` as the `osrm` backend.
- `geo-osrm`: Add a public estimate/fallback function that never performs HTTP (same haversine math as today’s OSRM miss path).
- `planner-service-sse-bridge`: Default `ToolContext.routing` comes from `get_routing_provider()`, not a hardcoded `OsrmRoutingProvider()`.
- `trips-repository-service`: Default injected routing for generate-adjacent persist/edits is `get_routing_provider()`, not a hardcoded `OsrmRoutingProvider()`.

## Impact

- **Backend:** `src/config.py`, `.env.example`, `src/geo/osrm.py`, `src/planner/routing_provider.py`, `src/planner/service.py`, `src/trips/service.py`; tests under `tests/planner/` and `tests/geo/`; `docs/context.md` after validate.
- **APIs / FE:** No new endpoints or DTO fields. `leg_polyline` / GeoJSON LineStrings may be absent; Point features already specified.
- **AGENT.md:** Geo only via `src/geo/`; `travel_engine` stays pure; all env via `get_settings()`; SSE still `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`.
- **Ops:** Default local/prod generate no longer depends on public OSRM. Operators with a real router set `ROUTING_BACKEND=osrm`.
- **Future (out of this change):** paid routing = same factory; Layla guidebook = richer `write_narrative` / export on saved `Trip` + schedule, not a generate-time map job.
