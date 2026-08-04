## Context

P5 delivers a real `PlannerService.generate` + compiled graph; trips/planner HTTP remain stubs. The archived design change produced `docs/steps/step6.md` and main spec `p6-planner-api-persistence`. Code inspection confirms the suggestion’s core gap: `travel_engine` never sets polylines, while `TripPlace.polyline` and blueprint GeoJSON expect them; `geo.osrm.get_route` already returns `encoded_polyline`. Blueprint also promises anonymous claim and `accommodation_label`. This design change locks how to adopt `docs/steps/step6_suggestion.md` as P6 v2 **before** implementation batches, without violating AGENT.md.

## Goals / Non-Goals

**Goals:**

- Make `step6.md` the v2 hardened Cursor contract (order **6.0 → 6.5**).
- Close polyline gap via Protocol DI (not new geo package APIs, not router OSRM).
- Lock SSE: one terminal frame, trip save before `trip_id`, proxy-safe headers, explicit poll timeout.
- Restore claim + cache-persists-trip + accommodation_label; keep Protocol Redis swap and fail-open.
- Keep efficiency: skip LLM tool loop on cache hit; polyline calls only after route order is known.

**Non-Goals:**

- Implementing application code in this change (docs/specs/tasks only).
- P7 edit/replan HTTP; Redis in docker-compose; LLM spend caps.
- Redesigning LangGraph, travel_engine scoring, or LLM gateway.
- Making GeoJSON require live OSRM on read.

## Decisions

1. **Canonical prompt = suggestion v2**  
   Copy/adopt `docs/steps/step6_suggestion.md` into `docs/steps/step6.md` (keep suggestion file as provenance or note “merged”). Agents implement from `step6.md` only.  
   *Alternatives:* patch v1 piecemeal → rejected (easy to miss locks); implement from suggestion path only → rejected (breaks “read stepN.md” convention).

2. **Polyline via `RoutingProvider.route_polyline` after optimize**  
   Thin adapter over existing `get_route`; `OptimizeResult.leg_polylines` + `day_polyline`; tools copy onto schedule stops. Fail-soft `None` if `fallback_used`. Max ~N+1 route calls/day after permutation pick — not geometry on every matrix pair.  
   *Alternatives:* only `day_polyline` (cheaper) → rejected for MVP because model column is per-`TripPlace`; new OSRM “table with geometry” → rejected (new API surface).

3. **SSE terminal buffer in router**  
   Non-terminal events yield immediately; terminal events buffer until task completes; then `save_from_state` (usable itinerary only) → enrich → **one** yield. Service stays HTTP-agnostic. Poll with `asyncio.wait_for(queue.get(), timeout=1.0)` + disconnect cancel.  
   *Alternatives:* service emits trip_id → rejected (DB/HTTP coupling); double emit → client bugs.

4. **Cache hit skips tool loop only**  
   Cached value = JSON subset of final `TravelState` (`schedule` with polylines, `itinerary`, prefs fields) sufficient for SSE + `save_from_state`. Each hit creates a **new** Trip row (new `trip_id`).  
   *Alternatives:* return cached trip_id → rejected (wrong owner/session; no auto-save for new guest).

5. **MVP cache key lock (resolves suggestion ambiguity)**  
   Key = `sha256(f"{destination_id}:{sha256(normalized_raw_input)}:{days_or_0}:{round(base_lat,3)}:{round(base_lng,3)}")` for router-level lookup **before** graph. Document that preference-semantic key (interests/budget) is a post-MVP refinement once parse can run once without dual invoke. Still include rounded base coords.  
   *Alternatives:* parse-once in router then preference key → better semantic hits but adds LLM before every generate / couples router to prefs; defer to follow-up if needed. Full generate then cache-only on second identical body → matches raw_input hash MVP.

6. **Claim restored as first-class**  
   `POST /trips/{id}/claim` + `claim_for_user`: `user_id IS NULL` + session match → set user; else 403/409. DELETE stays `require_auth` (intentional).  
   *Alternatives:* optional helper only → rejects blueprint promise.

7. **Proxy + frontend docs**  
   StreamingResponse headers locked; context.md deployment + “use fetch not EventSource” notes on 6.5 ship.

8. **Principles preserved**  
   Router → Service → Repository; no redis/litellm in domain routers; travel_engine I/O only through injected `RoutingProvider`; sole graph entry `PlannerService.generate`; Redis fail-open / cache miss; absolute min-places 409 pre-graph.

## Risks / Trade-offs

- [P5.14 still blocked on live LLM] → Mitigation: this change is plan-only; implementation gate remains P5 complete.
- [N+1 OSRM latency on build_route] → Mitigation: only after winning order; None on fallback; optional later “day polyline only” optimization if smoke too slow.
- [Raw-input cache key misses semantic duplicates] → Mitigation: documented MVP; prefer correctness of persist-on-hit over perfect cache hit rate.
- [Claim IDOR if session weak] → Mitigation: same wandr_session cookie rules as generate; 403 on mismatch; no anonymous DELETE.
- [Buffering terminal delays last frame until save] → Mitigation: expected; mid-stream tool events still live; save is DB-local.
- [Touching P4/P5 files in 6.0] → Mitigation: surgical Protocol + optimizer + tool field copy; FakeRoutingProvider updated; pytest regression required.

## Migration Plan

1. Apply this OpenSpec change’s doc task: replace `step6.md` with v2 content; leave `step6_suggestion.md` as reference or “merged into step6” note.
2. Sync delta specs into main specs when archiving / via sync.
3. Implementation batches (separate applies): `6.0` → `6.1` → `6.2` → `6.3` → `6.4–6.5`.
4. Rollback of this planning change: restore prior `step6.md` from git; discard this change folder.

## Open Questions

- None blocking for planning. Optional later: parse-once preference cache key if raw_input hashing proves too coarse in smoke.
