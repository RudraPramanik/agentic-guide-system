## Context

P6.0 closed route geometry; P6.1 landed `TripService.save_from_state` + ownership/claim. `PlannerService.generate` already runs the graph under `PLANNER_GENERATION_TIMEOUT_SECONDS` and emits via `on_event`. Step **6.2** (`docs/steps/step6.md`, SoT `docs/blueprint_final.md` v6.1) is the HTTP SSE adapter only: floor check, queue bridge, terminal-event buffering + persist, proxy headers.

**Current stubs:** `src/planner/router.py`, `src/planner/schemas.py` (~1 line each).  
**Already real:** `PlannerService.generate`, `TripService.save_from_state`, `DestinationService.get_by_id`, path rate limit for `/api/v1/planner/generate`, `wandr_session` in auth.

## Goals / Non-Goals

**Goals:**

- Live `POST /api/v1/planner/generate` streaming SSE while the background generate task runs.
- Absolute min-places floor → HTTP **409** `destination_not_ready` before graph/cache.
- Exactly **one** terminal SSE frame; `itinerary_done` enriched with `trip_id` when `save_from_state` returns a Trip.
- Proxy-friendly headers (`Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`).
- Keep `PlannerService` free of FastAPI streaming types.
- Declare `PLANNER_CACHE_TTL_SECONDS` now; cache helpers no-op miss until 6.4.

**Non-Goals:**

- Trips CRUD / GeoJSON / claim HTTP (6.3).
- Redis / real `CacheBackend` / cache hit path (6.4).
- Full pytest suite / `scripts/test_p6_smoke.py` / P6-complete context stamp (6.5).
- Changing `PlannerService.generate` signature beyond optional passthrough if needed for `days` (prefer not).

## Decisions

### D1 — Router is the only SSE adapter (Ports & Adapters)

**Choice:** Implement the queue + `StreamingResponse` loop in `src/planner/router.py` exactly as step6.2 sketches: `on_event` → `queue.put_nowait`; poll with `asyncio.wait_for(queue.get(), timeout=1.0)`; buffer `TERMINAL_EVENTS`; after task done, optionally `save_from_state`, yield one terminal frame.

**Why:** Matches locked v2 fix (no raw/double `itinerary_done`); keeps service HTTP-agnostic per `planner-service-sse-bridge`.

**Alt:** Service returns an async iterator — rejected (would couple service to SSE framing).

### D2 — Floor check before any graph or cache

**Choice:** After `DestinationService.get_by_id`, if `dest.place_count < PLANNER_ABSOLUTE_MIN_PLACES`, raise `DestinationNotReadyError` (409, code `destination_not_ready`, details include `place_count`). This is a **JSON** `WandrError` response (handler already in `main.py`), not an SSE `error` event — generation never starts.

**Why:** Locked in step6 + blueprint; avoids LLM spend on empty catalogs. Blueprint says "409/422"; step6 locks **409** — follow step6.

**Where:** Add exception on `src/destinations/exceptions.py` (same domain as place_count ownership).

### D3 — Cache stubs for 6.2 (always miss)

**Choice:** Add `src/planner/cache.py` with:

- `maybe_get_cached_state(...) -> None` always (no Redis yet).
- `_replay_cached(...)` stub that raises `NotImplementedError` or is documented unused until 6.4.

Router still calls `maybe_get_cached_state` so 6.4 is a wire-up, not a rewrite of `event_gen`.

**Why:** step6.2 explicitly allows a no-op miss checker; keeps cache-hit-still-persists path shape intact.

### D4 — `days` and `accommodation_label` handling

**Choice:**

- `PlanRequest.days` / `accommodation_label` are accepted on the body (blueprint-complete schema).
- **6.2 does not** extend `PlannerService.generate` to take them unless apply finds a zero-cost passthrough already planned.
- `days`: preference node continues to parse from `raw_input` (existing P5). Optional `days` is reserved for **6.4 cache key** (`days_or_0`) and may be merged into initial state in a tiny follow-up if apply proves clients need it before parse — prefer documenting as "accepted, cache-key-ready; graph still parses from raw_input in 6.2".
- `accommodation_label`: display-only; may be echoed onto the buffered `itinerary_done` payload if present; **not** written to Trip columns (no invented columns).

**Why:** Avoid widening the generate contract mid-SSE land; step6.2 prompt does not pass `days` into `generate()`.

### D5 — Session cookie alignment with auth (hardening vs literal step6 snippet)

**Choice:** Reuse auth constants/pattern: cookie name `wandr_session`, `samesite="lax"`, `secure` when `ENVIRONMENT == "production"`, `max_age=30*24*3600`. Prefer **`httponly=True`** (matches `src/auth/router.py`) over the step6 snippet's `httponly=False`.

**Why:** Auth already sets httponly; False would weaken guest ownership cookie security for no product benefit (frontend uses `fetch` credentials, not JS cookie reads for ownership). Document as intentional hardening vs the illustrative snippet.

**Alt:** Blind copy `httponly=False` — rejected.

### D6 — DB session lifecycle during long SSE

**Choice:** Use request-scoped `Depends(get_db)` for the floor `get_by_id` and the post-task `save_from_state`. Do **not** open a second long-lived session inside the generate task (tools already acquire their own sessions per P5 preference). If pool pressure appears under concurrent generates, 6.5/ops can shorten hold by resolving destination early and creating a fresh session only for save — out of 6.2 unless apply hits idle-in-transaction issues.

**Why:** Matches existing FastAPI DI; blueprint's "short sessions in tools" already covers the graph path. Risk noted below.

### D7 — `sse_frame` helper

**Choice:** Small local helper (or module-private function) formatting `event: …\ndata: …\n\n` with `json.dumps`. No new package. SSE is **not** wrapped in `ApiResponse`.

### D8 — Disconnect / finally cancel

**Choice:** On `request.is_disconnected()` cancel task and break; `finally` cancel if not done. Do not emit a second terminal after cancel if one was already buffered — if disconnect mid-stream with no terminal yet, stream ends without forcing an `error` frame (client already gone). Service timeout still emits `error` via `on_event` → buffered terminal.

### D9 — Save only on buffered `itinerary_done` with usable `task.result()`

**Choice:** Match step6: if terminal is `itinerary_done` and `task.result()` succeeds, call `save_from_state`; enrich `trip_id` only when Trip is not `None`. `error` / `clarification_needed` → yield as-is, no save. If `itinerary_done` then task exception → one terminal **without** `trip_id` (failure path in step6 validation).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Holding `get_db` session across ≤45s SSE | Tools use their own sessions; save is late flush+commit. Monitor pool; harden in 6.5 if needed. |
| `put_nowait` from sync `on_event` called on event loop | Same pattern as blueprint; keep `on_event` sync and non-blocking. |
| Double terminal if service emits two | Buffer overwrites `pending_terminal` (last wins) but still yield **once** — document; 6.5 tests assert single frame. |
| Cookie httponly divergence from step6 snippet | Prefer auth alignment (`True`); note in apply + context when 6.2 lands. |
| `days` ignored by graph in 6.2 | Accepted tradeoff; cache key + optional state merge deferred/documented. |
| Leftover untracked `openspec/changes/p6-1-trips-repo-service` vs archive | Cleanup housekeeping (delete stale active dir); not a 6.2 code blocker. |
| Blueprint 6.4 cache key (interests/budget) vs step6 v2 (raw_input hash) | Follow **step6 v2** when 6.4 lands; out of 6.2. |

## Migration Plan

1. Implement config + exception + schemas + cache stub + router + `main.py` register.
2. Run step6.2 validation: route registered; `PlannerService` has zero `StreamingResponse`/`is_disconnected` matches; floor → 409.
3. Update `docs/context.md`: mark 6.2 ✅, Next → 6.3, live endpoint row, remove planner HTTP from stubs; note proxy buffering + fetch-not-EventSource (can land with 6.2 or wait for 6.5 per cadence — prefer brief notes in context with 6.2).
4. No DB migration. Rollback = unregister router / revert files.

## Open Questions

Resolved in this design unless user overrides:

1. **httponly:** use auth's `True` (recommended) — confirm at apply if product needs JS-readable session (unlikely).
2. **`days` into generate:** leave unused by graph in 6.2; only schema + future cache key.
3. **DB hold:** ship with request-scoped session; revisit only if pool exhaustion shows in smoke.
