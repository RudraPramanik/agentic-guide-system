## 1. Extract shared ingest

- [x] 1.1 Move `seed_places` / seed-from-existing-destination (Overpass around stored `lat`/`lng`, per-POI upsert, `place_count` update) into `src/destinations/ingest.py` (or equivalent under `src/destinations/`). Geo only via `src.geo`. No httpx. No LLM.
- [x] 1.2 Thin `scripts/seed_destination.py` to argparse + `geocode` miss → exit 1 + session commit calling the shared ingest. Confirm CLI import path still works for existing tests.

## 2. Settings, DTO, limiter

- [x] 2.1 Add `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` (default 5) and `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` (default 60) via `get_settings()`. Do **not** add a UUID prepare path to `_route_limit_table`.
- [x] 2.2 Add `PrepareIn` (optional `radius_km`, default 30, max 50) and `DestinationPrepareOut` (`destination_id`, `status` ready|preparing, `place_count`) in `src/destinations/schemas.py`.
- [x] 2.3 Add IP-keyed prepare limiter dependency (`{ip}:dest_prepare`), fail-open, `RateLimitedError` 429 — same pattern as `rate_limit_trip_edit` but no `require_auth`.

## 3. Service + HTTP

- [x] 3.1 Implement `DestinationService.prepare`: 404 if missing; if `place_count >= PLANNER_ABSOLUTE_MIN_PLACES` return ready without Overpass; else cache in-flight lock, spawn `asyncio.create_task` with its own `AsyncSessionLocal`, clear lock in `finally`. Concurrent prepare must not start a second scrape.
- [x] 3.2 Add `POST /api/v1/destinations/{destination_id}/prepare` (auth None) on the destinations router: limiter dep → service only → `ApiResponse`; HTTP 200 ready / 202 preparing. Do not scrape inside search GET.

## 4. Tests

- [x] 4.1 Unit/API tests: unknown id 404; already-at-floor 200 ready and Overpass not called; below-floor 202 and ingest scheduled; concurrent second call 202 without second fetch; limiter 429; limiter exception fail-open; `radius_km` > 50 validation error.
- [x] 4.2 Keep CLI seed tests green after the ingest extract (`tests/scripts/test_seed_destination.py` or equivalent).

## 5. Frontend contract + checkpoint

- [x] 5.1 Update `docs/FE_guide.md`: destinations matrix + prepare DTO; MVP flow search → prepare → poll readiness (~2s, ~120s client timeout, first sparse poll is not failure) → guest generate; 409 is place floor not login/SSE; search does not scrape; country/region out of scope; prepare 5/min in the rate-limit table.
- [x] 5.2 Update `docs/context.md` Live endpoints + Implemented modules for prepare (no invented auth). Spot-check OpenAPI vs guide (schemas win).

## 6. Proof

- [x] 6.1 `python -m pytest` on destinations/scripts tests touched by this change (plus limiter tests if split out).
- [x] 6.2 Manual or mocked proof: search a non-Darjeeling place → prepare 202 → readiness `place_count` rises (or stays 0 on Overpass `[]`) → generate 409 until floor, then allowed. Guest, no login.
