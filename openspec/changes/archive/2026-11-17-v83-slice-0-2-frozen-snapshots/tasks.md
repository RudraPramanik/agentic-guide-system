## 1. Preflight

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 row 0.2, `docs/v8.2/repository_audit.md` sections 3 and 4, this change's `design.md`, and `specs/legacy-api-snapshots/spec.md`. List the files that will be read. The only writes are under `tests/snapshots/**` and `tests/fixtures/**`.
- [x] 1.2 Run the existing suite excluding `tests/snapshots`. First run was red because Postgres was down. After `docker compose up -d postgres`, the connection errors are gone. Remaining failures are local environment: `REDIS_URL` uses an `https` scheme, CORS is `http://localhost:3001`, and rate-limiter tests raise on that URL. Those tests and production code were not edited.

## 2. Snapshot harness

- [x] 2.1 Add `tests/snapshots/conftest.py` with the autouse fail-closed patches from design Decision 4: `geocode`, `geocode_search`, `chat_completion`, and `chat_with_tools` raise if called; `is_qdrant_available` returns false. Do not patch `httpx.AsyncClient`.
- [x] 2.2 Add one normalizer under `tests/snapshots/` that replaces UUID strings, ISO datetimes, and `wandr_session` values with `<uuid>`, `<datetime>`, and `<session>`. Leave lat, lng, counts, scores, day numbers, and stop order exact.
- [x] 2.3 Add a fixture loader that reads `tests/fixtures/snapshots/*.json` and compares a normalized body or an ordered `{event, data}` list. No update switch.

## 3. Destination search and readiness

- [x] 3.1 Seed a destination whose name matches the search query, store the request template under `tests/fixtures/snapshots/requests/`, and freeze the normalized 200 `ApiResponse`. Assert the geocoder patch was not called.
- [x] 3.2 Seed readiness counters with vector search unavailable and freeze the normalized 200 body, including `tier` and `message`. Do not call resolve or prepare.

## 4. Planner SSE

- [x] 4.1 Freeze the scripted progress run: `preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, then `itinerary_done`. Assert status 200, that order, one terminal, `cache-control: no-cache`, and `x-accel-buffering: no`. Patch `PlannerService.generate`. Do not compile the graph.
- [x] 4.2 Freeze a lone `error` terminal and a lone `clarification_needed` terminal, each appearing once.
- [x] 4.3 Freeze the double-terminal case: stub emits `itinerary_done` then `error`. The wire contains exactly one terminal. The router keeps the last one, so the fixture is `error`.
- [x] 4.4 Freeze the place-count floor: `place_count` 0 returns 409 `destination_not_ready` with no `event:` line, and the generate stub is not called. Do not require `tool_started` or `validation_done`.

## 5. Trip CRUD, guest and authenticated

- [x] 5.1 Freeze `GET /api/v1/trips` with no credentials as 401, using the error envelope (`success`, `code`, `message`). The body stays a bare error, not an `ApiResponse` success wrapper.
- [x] 5.2 Freeze guest `GET /api/v1/trips/{id}`: matching `wandr_session` is 200 `ApiResponse`; a different session is 403 and not 404.
- [x] 5.3 Freeze `DELETE /api/v1/trips/{id}` with no credentials as 401.
- [x] 5.4 Freeze `POST /api/v1/trips/{id}/claim` for an authenticated caller whose `wandr_session` matches an unclaimed trip as 200 `ApiResponse`.

## 6. GeoJSON

- [x] 6.1 Freeze points-only geojson for stops with null polylines: raw `FeatureCollection`, Point features, properties `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id`, coordinates `[lng, lat]`, no `success`/`data` wrapper.
- [x] 6.2 Freeze one decodable polyline as a LineString with properties `day` and `trip_id`. The read must not call a routing provider.

## 7. Day edits

- [x] 7.1 Freeze the four owner routes (reorder, remove, add, reoptimize) as 200 `ApiResponse`, injecting `FakeRoutingProvider` through the router the way `tests/trips/test_trip_edit_http.py` does. Reorder's fixture keeps stop order. Do not edit `travel_engine/`.
- [x] 7.2 Freeze the same four routes with no credentials as 401, and assert no routing provider is contacted.

## 8. Verify

- [x] 8.1 Run `pytest tests/snapshots -v` twice. Both runs pass, and the second run matches the same fixtures (normalization holds).
- [x] 8.2 Confirm the diff is only `tests/snapshots/**` and `tests/fixtures/**`. No new package, no `requirements.txt` edit, no production edit, no `docs/context.md` edit. Subslice 0.2's allowed paths forbid the context update the OpenSpec repo rule would otherwise ask for. Put the blueprint §19 completion report in the PR description, not in a new file.
