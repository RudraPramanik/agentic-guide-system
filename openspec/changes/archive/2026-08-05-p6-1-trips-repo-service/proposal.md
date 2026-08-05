## Why

P6.0 closed the polyline gap so schedules carry `leg_polyline` / `day_polyline`, but trips persistence is still a one-line stub. Without `TripService.save_from_state`, ownership, and claim, P6.2 cannot enrich `itinerary_done` with a real `trip_id`, and P6.3 cannot expose CRUD/GeoJSON. Step **6.1** in `docs/steps/step6.md` (SoT: `docs/blueprint_final.md` v6.1) lands that service/repository layer now.

## What Changes

- Implement `src/trips/exceptions.py` — `TripNotFoundError` (404), `TripForbiddenError` (403), `TripAlreadyClaimedError` (409).
- Implement `src/trips/schemas.py` — `TripOut` / `TripPlaceOut` (include `suggested_start_time`, `visit_duration_min`, `polyline`, joined lat/lng; no invented columns).
- Implement `src/trips/repository.py` — `TripRepository(BaseRepository[Trip, UUID])` with `list_by_user`, `list_by_session`, `get_with_places` (eager TripPlace + Place coords).
- Implement `src/trips/service.py` — `save_from_state` (UoW, locked field map including `polyline` ← `leg_polyline`), `assert_can_access`, `claim_for_user`; service owns commit; repository flush-only.
- Add minimal ORM relationships on `Trip` ↔ `TripPlace` ↔ `Place` so `get_with_places` can eager-load without ad-hoc N+1 queries (models today have zero `relationship()` usage).
- Unit-testable surface via `db_session` (import-surface validation in this step; full pytest suite lands with 6.5 per step6.md).
- Out of this change: FastAPI trips router, planner SSE `/generate`, Redis/cache, GeoJSON builder HTTP, P7 edits.

## Capabilities

### New Capabilities

- `trips-repository-service`: Trip repository + service persistence, ownership policy, claim transfer, and response schemas for step 6.1 (no HTTP router).

### Modified Capabilities

- `p6-planner-api-persistence`: Pin that step 6.1 delivers the service/repo/claim surface only; HTTP claim/CRUD remain 6.3; `save_from_state` return type is `Trip | None`.
- `core-domain-models`: Allow optional SQLAlchemy relationships on Trip/TripPlace/Place for eager load in `get_with_places` (no column/migration changes).
- `route-geometry-polyline`: Confirm 6.1 maps `stop["leg_polyline"]` → `TripPlace.polyline` on persist (GeoJSON HTTP still 6.3).

## Impact

- **Code:** `src/trips/{exceptions,schemas,repository,service}.py` (stubs → real); `src/trips/models.py` (+ Place relationship side if needed); possibly `src/places/models.py` for backref/relationship only.
- **APIs:** None registered in 6.1 (router stays stub).
- **Deps:** No new packages.
- **AGENT.md:** Router → Service → Repository; service owns commit; no PlannerService calls from trips; no litellm/geo in trips; envelopes deferred until 6.3 router.
- **Non-goals:** `trips/router.py`, planner HTTP SSE, Redis, `build_geojson`, DELETE/list HTTP, P7 edit ops, context.md P6-complete stamp.
- **Prerequisites (verified):** P5.1–5.14 ✅; P6.0 `route_polyline` + schedule day-dict with polylines ✅; Trip/TripPlace models real; trips repo/service/schemas/exceptions still stubs; `wandr_session` already used in auth.
