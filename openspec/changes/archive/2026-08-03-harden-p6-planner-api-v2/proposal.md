## Why

The current P6 build contract (`docs/steps/step6.md`) is solid on layering and SSE basics, but a hardened critique (`docs/steps/step6_suggestion.md`) found real product gaps: route geometry never flows into `TripPlace.polyline` (so GeoJSON cannot draw lines), terminal SSE/`trip_id` timing is ambiguous, cache hits skip persistence, anonymous trip claim (promised in the blueprint) was downgraded, and reverse-proxy SSE buffering would break the stated self-hosted deploy. Adopting those locks now keeps P6 efficient and principle-aligned before HTTP implementation starts.

## What Changes

- Adopt `docs/steps/step6_suggestion.md` as the **canonical P6 Cursor build contract**, replacing the content of `docs/steps/step6.md` (v2: steps **6.0–6.5**).
- Add **step 6.0** cross-phase patch: `RoutingProvider.route_polyline()` → `OptimizeResult` polylines → schedule/`TravelState` → `save_from_state` (reuses existing `geo.osrm.get_route`; no new OSRM API type).
- Lock **exactly one** enriched terminal SSE frame (`itinerary_done` with `trip_id` when saved); buffer terminal events; `asyncio.wait_for(queue.get(), timeout=1.0)`.
- Require SSE streaming headers (`Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`) plus context deployment note for proxy buffering.
- Restore blueprint **claim** flow: `POST /api/v1/trips/{id}/claim` + `TripService.claim_for_user` (200 / 403 / 409).
- Lock **cache hit still persists** a new Trip from cached `TravelState` subset; skip tool loop only.
- Restore `PlanRequest.accommodation_label` (display-only); explicit `save_from_state` field mapping including `polyline`.
- Document frontend constraint: POST SSE → `fetch()` + manual parse (not `EventSource`).
- Update main OpenSpec capability `p6-planner-api-persistence` to match v2 locks; add a focused route-geometry capability for the 6.0 contract.
- **Non-goals:** implementing P6 HTTP/code in this change (docs + specs only); P7 edit/replan; Redis in docker-compose; daily LLM spend caps; changing LLM gateway or inventing a second graph invoke path.
- **Gate:** do not apply P6 implementation batches until P5.14 smoke is green (or an explicitly accepted documented blocker).

## Capabilities

### New Capabilities
- `route-geometry-polyline`: Protocol + optimizer threading of encoded polylines into schedule/TripPlace for GeoJSON LineStrings, with fail-soft `None` when OSRM falls back to haversine.

### Modified Capabilities
- `p6-planner-api-persistence`: Build order becomes 6.0→6.5; claim endpoint restored; SSE terminal buffering + proxy headers; cache hits still persist; `accommodation_label`; explicit persistence mapping; frontend/deploy notes in context on ship.

## Impact

- **Docs:** `docs/steps/step6.md` superseded by v2 content from `step6_suggestion.md`; later `docs/context.md` ship notes (on 6.5 apply).
- **Code (future apply batches):** `src/travel_engine/protocols.py`, `route_optimizer.py`, `src/planner/routing_provider.py`, build_route/build_schedule tools, `TravelState` schedule shape; `src/trips/*`; `src/planner/router.py` / schemas; `src/core/cache/*` + rate limiter Redis; tests/smoke.
- **APIs:** adds `POST /trips/{id}/claim`; enrich `itinerary_done` with `trip_id`; GeoJSON gains LineStrings when polylines exist.
- **AGENT.md:** preserves Router→Service→Repository, LLM gateway-only, geo via `src/geo/`, travel_engine purity via Protocol DI, fail-open Redis, no Redis imports in routers.
- **Efficiency:** polyline adds O(N)+1 `get_route` calls per day after order is chosen (not O(N²) matrix geometry); cache still avoids the LLM tool loop while keeping auto-save.
