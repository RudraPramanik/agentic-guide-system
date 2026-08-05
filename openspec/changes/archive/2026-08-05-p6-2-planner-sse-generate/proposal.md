## Why

`PlannerService.generate` (P5.12) and `TripService.save_from_state` (P6.1) are real, but clients still have no HTTP path to stream a plan or receive a persisted `trip_id`. Step **6.2** in `docs/steps/step6.md` (SoT: `docs/blueprint_final.md` v6.1) lands the SSE adapter: floor check → queue+task → buffer terminal → save → **one** enriched `itinerary_done`, with reverse-proxy streaming headers.

## What Changes

- Add `PLANNER_ABSOLUTE_MIN_PLACES` (default 10) and `PLANNER_CACHE_TTL_SECONDS` (default 3600, used from 6.4) to `src/config.py`.
- Implement `src/planner/schemas.py` — `PlanRequest` with `destination_id`, `raw_input`, optional `days` / `base_lat` / `base_lng` / `accommodation_label` (display-only, restored per blueprint).
- Implement `src/planner/router.py` — `POST /api/v1/planner/generate` as `StreamingResponse` (`text/event-stream`) with locked terminal-event buffering, disconnect cancel, proxy headers, and `wandr_session` cookie ensure.
- Add `DestinationNotReadyError` (409, code `destination_not_ready`) for the absolute min-places floor — raised **before** graph or cache work.
- Stub cache helpers for 6.2: `maybe_get_cached_state` always misses; `_replay_cached` exists but is unused until 6.4 wires Redis/`CacheBackend`.
- Register planner router in `main.py`.
- Out of this change: trips HTTP CRUD/GeoJSON/claim (6.3), Redis/`CacheBackend` (6.4), full pytest/smoke/context P6 stamp (6.5).

## Capabilities

### New Capabilities

- `planner-sse-generate`: HTTP SSE adapter over `PlannerService.generate` — PlanRequest, floor check, queue polling, terminal buffering + `save_from_state` enrichment, proxy headers, session cookie.

### Modified Capabilities

- `p6-planner-api-persistence`: Pin that step 6.2 delivers the live generate SSE endpoint (single terminal frame + `trip_id` when saved); cache hit path remains a no-op miss until 6.4; trips HTTP still 6.3.
- `planner-service-sse-bridge`: Confirm `PlannerService` stays free of `StreamingResponse` / `Request` / disconnect checks — router is the sole SSE adapter.

## Impact

- **Code:** `src/config.py`; `src/planner/{schemas,router}.py` (stubs → real); `src/planner/cache.py` (thin 6.2 no-op miss stubs); `src/destinations/exceptions.py` (+ `DestinationNotReadyError`); `src/main.py` (register router).
- **APIs:** `POST /api/v1/planner/generate` (SSE; `optional_auth`). JSON error path for floor/missing destination via existing `WandrError` handler (not SSE).
- **Deps:** No new packages.
- **AGENT.md:** Router → Service → Repository; SSE wrapped by service `wait_for` ceiling already; no litellm/geo in router; rate limit already on path table (do not double-limit).
- **Non-goals:** trips router, Redis backends, real cache hit/set, P7 edits, `docs/context.md` P6-complete stamp (update Next → 6.3 only after 6.2 validation).
- **Prerequisites (verified):** P5.1–5.14 ✅; P6.0 `route_polyline` ✅; P6.1 `save_from_state` / claim / schemas ✅; `PlannerService.generate` real; planner `router`/`schemas` still stubs; path rate limit for `/api/v1/planner/generate` already configured; `wandr_session` used in auth router.
