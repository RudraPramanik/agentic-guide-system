## 1. Config + 429 exception

- [x] 1.1 Add `RATE_LIMIT_TRIP_EDIT_REQUESTS: int = 20` and `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS: int = 60` to `src/config.py` Settings
- [x] 1.2 Add `RateLimitedError(WandrError)` in `src/core/exceptions.py` (`status_code=429`, `code="rate_limit_exceeded"`) so the global handler maps it
- [x] 1.3 Confirm `_route_limit_table` is unchanged (no UUID trip-edit path rows)

## 2. User-keyed rate limit dependency

- [x] 2.1 Create `src/trips/dependencies.py` with `async def rate_limit_trip_edit(payload: TokenPayload = Depends(require_auth)) -> TokenPayload`
- [x] 2.2 Call `get_rate_limiter().is_allowed(f"{payload.user_id}:trip_edit", requests, window)`; raise `RateLimitedError` when denied; catch Exception → fail open (return payload)
- [x] 2.3 Comment that middleware IP default may still apply (dual limit OK)

## 3. Edit HTTP routes

- [x] 3.1 Extend `src/trips/router.py`: `PATCH /{trip_id}/days/{day}/stops/reorder` body `ReorderStopsIn`, Depends `rate_limit_trip_edit` → `TripService.reorder_stops` → `ApiResponse[TripOut]`
- [x] 3.2 Add `DELETE /{trip_id}/days/{day}/stops/{place_id}` → `remove_stop`
- [x] 3.3 Add `POST /{trip_id}/days/{day}/stops` body `AddStopIn` → `add_stop`
- [x] 3.4 Add `POST /{trip_id}/days/{day}/reoptimize` → `reoptimize_day`
- [x] 3.5 Verify router imports: schemas + service + deps only — no DB, travel_engine, redis, litellm, planner

## 4. Thin HTTP tests + proof

- [x] 4.1 Add focused `tests/trips/` HTTP tests: OpenAPI includes four edit paths; owner reorder → 200 `TripOut`; guest → 401; other user → 403
- [x] 4.2 Mock/override limiter so 21st rapid edit same user → 429 `rate_limit_exceeded`; trip unchanged
- [x] 4.3 Optionally assert add overload / would-drop → 422 and re-GET matches pre-edit (if cheap with Fake routing DI)
- [x] 4.4 Run `python -m pytest tests/trips/ -v` (and full suite if green locally)

## 5. Context checkpoint

- [x] 5.1 Update `docs/context.md`: Last updated, Progress 7.3 ✅, Next → 7.4, live endpoints table (+ four edit rows), stubs note (edit HTTP now real; full 7.4 suite still pending), Implemented modules note for router/deps/rate-limit settings
