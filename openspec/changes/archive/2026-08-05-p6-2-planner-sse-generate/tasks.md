## 1. Config + exception + schemas

- [x] 1.1 Add `PLANNER_ABSOLUTE_MIN_PLACES: int = 10` and `PLANNER_CACHE_TTL_SECONDS: int = 3600` to `src/config.py` (via `get_settings()` only)
- [x] 1.2 Add `DestinationNotReadyError` to `src/destinations/exceptions.py` — HTTP 409, code `destination_not_ready`, details include `place_count`
- [x] 1.3 Implement `PlanRequest` in `src/planner/schemas.py` (`destination_id`, `raw_input`, optional `days` / `base_lat` / `base_lng` / `accommodation_label`)

## 2. Cache stub (always miss)

- [x] 2.1 Add `src/planner/cache.py` with `maybe_get_cached_state(...)` returning `None` and a documented `_replay_cached` stub unused until 6.4

## 3. SSE router

- [x] 3.1 Implement `src/planner/router.py`: `APIRouter(prefix="/api/v1/planner")`, `TERMINAL_EVENTS`, `sse_frame` helper, `POST /generate` with `optional_auth` + `get_db`
- [x] 3.2 Resolve `wandr_session` (create UUID if missing); align cookie flags with auth (`httponly=True`, `samesite=lax`, `secure` in production, 30-day max_age) per design D5
- [x] 3.3 Floor check: `DestinationService.get_by_id` → raise `DestinationNotReadyError` when `place_count < PLANNER_ABSOLUTE_MIN_PLACES`; default `base_lat`/`base_lng` from destination
- [x] 3.4 Event loop: queue + `create_task(PlannerService.generate(...))` (or `_replay_cached` when cache hits in 6.4); poll `wait_for(queue.get(), 1.0)`; buffer terminals; disconnect → `task.cancel()`
- [x] 3.5 After task done: on buffered `itinerary_done` + usable `task.result()`, call `TripService(db).save_from_state` and enrich `trip_id` when Trip returned; yield exactly one terminal frame; set proxy headers on `StreamingResponse`

## 4. Register + validation

- [x] 4.1 Register planner router in `src/main.py`
- [x] 4.2 Run step 6.2 route proof: `create_app()` has a path containing `planner/generate`
- [x] 4.3 Assert zero `StreamingResponse` / `is_disconnected` matches in `src/planner/service.py`
- [x] 4.4 Manual/TestClient failure path: destination `place_count=0` (or below floor) → HTTP 409 `destination_not_ready` (no generate)

## 5. Context checkpoint

- [x] 5.1 Update `docs/context.md`: mark 6.2 ✅, Next → 6.3, add planner router/schemas to implemented modules, live endpoint `POST /api/v1/planner/generate`, remove planner HTTP from stubs; note reverse-proxy buffering off + frontend `fetch()` (not EventSource)
