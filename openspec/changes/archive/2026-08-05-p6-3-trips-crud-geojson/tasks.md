## 1. GeoJSON builder + polyline decode

- [x] 1.1 Add pure Google-encoded polyline decoder in `src/trips/` (no new package; invalid/empty → skip, never raise)
- [x] 1.2 Implement `TripService.build_geojson(trip) → dict` FeatureCollection: Point per stop (Place coords + name/day/order/`suggested_start_time`); LineString(s) from decoded polylines (prefer per-day concat); Points-only when all polylines None
- [x] 1.3 Confirm `build_geojson` has zero OSRM/httpx/`src.geo` network imports

## 2. HTTP-facing TripService helpers

- [x] 2.1 Add get helper: `get_with_places` or `TripNotFoundError`, then `assert_can_access`
- [x] 2.2 Add `list_for_user(user_id, params)` returning items + total for pagination
- [x] 2.3 Add soft-delete helper: ownership assert + `repo.soft_delete` + commit
- [x] 2.4 Add claim wrapper: load trip + `claim_for_user` (404 if missing)

## 3. Trips router + registration

- [x] 3.1 Implement `src/trips/router.py`: `GET /`, `GET /{id}`, `GET /{id}/geojson`, `DELETE /{id}`, `POST /{id}/claim` per locked auth matrix; reuse `COOKIE_SESSION` from auth
- [x] 3.2 Comment DELETE `require_auth` asymmetry (intentional — no anonymous destructive actions)
- [x] 3.3 GeoJSON returns raw FeatureCollection (not `ApiResponse`); other JSON routes use envelopes; claim/ownership errors via global WandrError handler (no ad-hoc try/except)
- [x] 3.4 Register trips router in `src/main.py`

## 4. Validation and tests

- [x] 4.1 Run step 6.3 path check: create_app routes include `trips` and `claim`
- [x] 4.2 Add focused tests: geojson LineString when polylines present; Points-only when None; ownership 403; claim 200 / wrong session 403 / re-claim 409; list 401 without auth
- [x] 4.3 Run `python -m pytest tests/trips/ -v` (and related) — green before context stamp
- [x] 4.4 Import guard: no `redis` / `httpx` / `litellm` under `src/trips`

## 5. Context

- [x] 5.1 Update `docs/context.md`: Progress 6.3 ✅, Next → P6.4; list trips router + `build_geojson` as real; add live trips endpoints; remove trips HTTP from stubs; note claim needs retained `wandr_session` after login
- [x] 5.2 Do not implement Redis/cache (6.4); do not mark P6 complete; do not add P7 edit routes
