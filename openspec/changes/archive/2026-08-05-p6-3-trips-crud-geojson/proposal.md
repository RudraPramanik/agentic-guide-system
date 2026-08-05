## Why

P6.1 shipped trip persistence/ownership/claim helpers and P6.2 now saves trips from SSE `itinerary_done`, but `src/trips/router.py` is still a one-line stub — clients cannot list/get/delete trips, claim anonymous trips after login, or render maps via GeoJSON. Step **6.3** in `docs/steps/step6.md` (SoT: `docs/blueprint_final.md` v6.1) lands that HTTP surface now that geometry and save paths are real.

## What Changes

- Implement `TripService.build_geojson(trip)` — FeatureCollection from already-loaded places/polylines/coords; Points always; LineStrings when encoded polylines decode; no live OSRM/httpx on read.
- Add thin service helpers the router needs (get/list/soft-delete wrapping existing repo + ownership) so routers never touch DB.
- Implement `src/trips/router.py` endpoints per locked auth matrix:
  - `GET /api/v1/trips` → `PaginatedResponse[TripOut]` (`require_auth`)
  - `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` (`optional_auth` + ownership)
  - `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (**public**; envelope exception)
  - `DELETE /api/v1/trips/{id}` → 204 (`require_auth` + ownership; intentional vs guest GET)
  - `POST /api/v1/trips/{id}/claim` → `ApiResponse[TripOut]` (`require_auth` + session + unclaimed)
- Register trips router in `main.py`.
- Pure Google-encoded polyline decode helper (no new package) so LineStrings use road geometry from P6.0, not stop-to-stop chords.
- Focused router/geojson tests; full P6 suite remains 6.5.
- Out of this change: Redis/cache (6.4), P6 ship checklist/smoke (6.5), P7 edit/replan routes.

## Capabilities

### New Capabilities

- `trips-http-crud-geojson`: Trips FastAPI CRUD + public GeoJSON + claim HTTP; `build_geojson`; ownership/claim error mapping via existing WandrError handler.

### Modified Capabilities

- `p6-planner-api-persistence`: Mark step 6.3 as the delivery of trips CRUD/GeoJSON/claim HTTP (previously deferred from 6.1/6.2); keep 6.4–6.5 forward-locked.
- `trips-repository-service`: Extend service surface with `build_geojson` (+ thin get/list/delete wrappers used by HTTP); claim HTTP now in scope via router (service helpers already real).

## Impact

- **Code:** `src/trips/router.py` (stub → real); `src/trips/service.py` (+ `build_geojson` + thin HTTP-facing helpers); optional small `src/trips/geojson.py` or private decode helper; `src/main.py` register trips router.
- **APIs:** Five trips routes become live (see auth matrix above). GeoJSON returns raw FeatureCollection, not `ApiResponse` (map-tool exception; document in router).
- **Deps:** No new packages — polyline decode is pure Python.
- **AGENT.md:** Router → Service → Repository; envelopes for JSON CRUD; no redis/litellm/geo httpx in trips; soft-delete via BaseRepository; DELETE auth asymmetry commented in code.
- **Non-goals:** Redis/cache, planner SSE changes, P7 edit ops, marking P6 complete in `docs/context.md` (only Progress 6.3 → Next P6.4 after green apply).
- **Prerequisites (verified this propose):**
  - `docs/context.md`: P6.0–6.2 ✅, Next → P6.3
  - `POST /api/v1/planner/generate` registered; trips routes absent
  - `TripService.save_from_state` / `assert_can_access` / `claim_for_user` real; `TripOut`/`TripPlaceOut` real
  - `trips/router.py` still stub (~1 line); `get_with_places` eager-loads Place coords + polylines
  - `day_polyline` is **not** a DB column (6.1 design) — GeoJSON reconstructs from per-stop `TripPlace.polyline`
