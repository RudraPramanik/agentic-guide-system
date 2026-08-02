## Context

P0–P5 (through the tool-loop agent + `PlannerService.generate` bridge) deliver generation without an HTTP SSE surface or trip persistence. Models for `Trip` / `TripPlace` / `TripEditEvent` already exist; `src/trips/{repository,service,router,schemas}.py` and `src/planner/{router,schemas}.py` remain ~1-line stubs. Rate limiting already exposes `RateLimiterBackend` + `InMemoryRateLimiter` with a documented Redis extension point; `REDIS_URL` exists in settings but no Redis client is wired. `PLANNER_ABSOLUTE_MIN_PLACES` is not in settings yet.

`docs/blueprint_final.md` **v6.1** locks P6 (6.1–6.5): trips save UoW + guest ownership, `POST /planner/generate` StreamingResponse with queue + disconnect cancel, trips CRUD + GeoJSON, Redis-backed rate limit + planner cache, backend ship checklist. `docs/steps/step6.md` is empty. This design change authors the hardened Cursor prompt (and OpenSpec alignment), not the production HTTP/persistence code itself.

**Prerequisite gate:** Do not implement P6 code until P5 ship criteria pass (5.1–5.14, including `scripts/test_agent.py` + context Next → P6.1). `PlannerService.generate` with `on_event` + `wait_for` is the HTTP layer’s only generation entry — do not invent a second graph invoke path.

Constraints (AGENT.md): Router → Service → Repository; LLM/geo only via gateways; evaluation never skipped; SSE generation timeout; all env via `get_settings()`; `ApiResponse` / `PaginatedResponse` envelopes.

## Goals / Non-Goals

**Goals:**

- Author `docs/steps/step6.md` in the **step5 shape**: Decision/Fix log, prerequisites, architecture, locked decisions, sub-steps **6.1–6.5**, FAILURE BOUNDARY per code step, ✅ validation, pytest plan, smoke/ship checklist.
- Encode blueprint v6.1 locks with explicit **abstraction layers** so providers (cache, rate limiter, routing, LLM) swap via settings/DI without rewriting routers or services.
- Encode **named fallbacks** for every external dependency (Redis, OSRM already via provider, LLM already via gateway).
- Define **batched OpenSpec implementation clusters** for speed.

**Non-Goals:**

- Implementing production trips/planner HTTP/Redis code in *this* change’s apply — primary apply = write the prompt.
- P7 edit/replan API (`reorder` / `remove` / `add` / `reoptimize` HTTP).
- Sustained daily LLM spend caps, multi-region Redis, or Qdrant/health component_status upgrades.
- One OpenSpec propose→apply→archive ceremony per micro-step during implementation.
- Replacing `PlannerService.generate` with a router-inline graph invoke.

## Decisions

### D0 — Process: blueprint vs step prompt vs OpenSpec cadence

**Choice:** Keep three layers distinct:

| Layer | Role |
|-------|------|
| `docs/blueprint_final.md` | Product/architecture SoT |
| `docs/steps/step6.md` | Agent build contract (sub-steps, validation, tests) |
| OpenSpec change | Propose → apply → archive for *batches* of work |

**Apply cadence for P6 implementation (after this design change archives):**

1. `6.1` — trips repository + `TripService.save_from_state` + guest ownership helpers + schemas/exceptions
2. `6.2` — planner schemas + `POST /planner/generate` SSE StreamingResponse (queue, disconnect cancel, absolute min-places floor) + wire `optional_auth` / auto-save
3. `6.3` — trips CRUD router + GeoJSON builder
4. `6.4–6.5` — Redis rate limiter + `CacheBackend` planner cache + pytest/smoke + backend ship checklist + `context.md`

Do **not** run full propose→archive for every micro-step; `step6.md` already locks the contract.

### D1 — Layering & DIP: routers never know Redis / OSRM / litellm

**Choice (LOCKED):** Strict dependency inversion at HTTP and infrastructure boundaries.

```
Router (FastAPI)
  → PlannerService / TripService   # domain orchestration only
      → TripRepository / DestinationService / Evaluation path
      → CacheBackend (Protocol)     # get/set/delete — InMemory | Redis
  Middleware
      → RateLimiterBackend (Protocol)  # already exists — InMemory | Redis
  ToolContext.routing
      → RoutingProvider (Protocol)     # already exists — Osrm | Fake
  LLM
      → core/llm/client.py only        # litellm swap via LLM_MODEL env
```

**Factory selection (LOCKED):** `get_rate_limiter()` / `get_cache_backend()` choose concrete impl from `get_settings().REDIS_URL` (empty → in-memory). Call sites never import `redis` directly outside the backend module. Changing Redis vendor / in-memory ↔ Redis MUST be zero router/service logic change.

**Alternatives considered:** Inject Redis client into routers — rejected (violates layering, hard to test). Single god `Infrastructure` class — rejected (over-couples).

### D2 — SSE: router owns StreamingResponse; service stays HTTP-agnostic

**Choice (LOCKED):** Keep `PlannerService.generate(..., on_event=...)` as the sole generation runner. The HTTP router:

1. Pre-checks destination existence + `place_count >= PLANNER_ABSOLUTE_MIN_PLACES` (else 409/422 — **no graph, no LLM spend**).
2. Creates `asyncio.Queue` and an `on_event` that `put_nowait`s `(event, data)`.
3. Starts `generate(...)` as a **background task**.
4. Async generator yields `text/event-stream` frames while polling the queue; polls `request.is_disconnected()` → cancel background task.
5. Outer ceiling: rely on service `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`; on timeout/error emit SSE `error` then close.
6. On successful `itinerary_done` path: authenticated users → `TripService.save_from_state`; guests → save with `session_id` only (or defer save until client explicitly saves — **LOCKED preference:** auto-save for both with `user_id=None` for guests so trip_id is always available in final event payload when generation succeeds).

**Must NOT:** await full `generate` then dump buffered events (blueprint: never await-full-invoke-then-dump). **Must NOT:** put FastAPI `Request` / `StreamingResponse` types inside `PlannerService`.

**Alternatives considered:** Rewrite service as async generator — rejected (breaks P5 callback tests; couples service to SSE framing). LangGraph streaming callbacks only — rejected (still need Queue + disconnect cancel at HTTP edge).

### D3 — Pre-graph absolute min-places floor

**Choice:** Add `PLANNER_ABSOLUTE_MIN_PLACES` (default **10**) to `Settings`. Router (via service helper, not raw repo) loads destination `place_count`; if below floor → HTTP **409** or **422** with stable error code `destination_not_ready` — **do not** enter tool loop. Soft readiness warnings (`PLANNER_MIN_READINESS_SCORE`) remain in-graph; this floor is the hard HTTP gate.

**HTTP status (LOCKED for prompt):** Prefer **409 Conflict** with `ErrorResponse` code `destination_not_ready` (resource exists but not usable for planning). Document in Decision Log; do not flip between 409/422 mid-phase.

### D4 — Trip persistence Unit of Work + guest ownership

**Choice:**

- `TripRepository(BaseRepository[Trip, UUID])`: `list_by_user`, `list_by_session`, `get_with_places` (eager load TripPlace + Place as needed).
- `TripService.save_from_state(state, user_id, session_id) → Trip`: map itinerary/schedule/route → `Trip` + `TripPlace` rows in **one transaction**; flush/commit via existing session patterns; partial failure → **full rollback** (no orphan Trip without places).
- **Guest ownership (LOCKED):** unauthenticated access requires `wandr_session` cookie **exactly equal** to `Trip.session_id`; mismatch/missing → **403** (same as auth user hitting another's trip) — never 404 for existence-hiding in MVP (blueprint explicitly says 403).
- Claim-after-login: authenticated user may claim a guest trip when `session_id` matches (service method can land in 6.1 or be a thin helper used by later auth flow — prompt locks the rule; full “claim” endpoint optional if not in blueprint table — **LOCKED:** implement ownership checks + save; dedicated claim endpoint only if needed for tests — prefer save + get ownership).

**GeoJSON:** pure builder in `TripService.build_geojson(trip)` (or module helper) from stored polylines/coords — no live OSRM on GET. Public `GET .../geojson` per blueprint.

### D5 — Planner cache (Cache-Aside) with Protocol

**Choice:** Introduce `CacheBackend` Protocol:

```python
class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
```

- Key: `sha256(destination_id + sorted_interests + days + budget + round(base_lat,3) + round(base_lng,3))` — 1h TTL from settings.
- Cache at **parsed-preference** level (MVP tradeoff: free-text nuance beyond parse may be dropped on hit). Best-effort: miss or backend error → run agent fresh; never 500.
- Dev: `InMemoryCacheBackend`. Prod (`REDIS_URL`): `RedisCacheBackend`.
- Cache hit still emits a short SSE sequence ending in `itinerary_done` (or single cached payload event) — prompt locks: return cached itinerary via SSE without re-running tools; still respect rate limit.

### D6 — Redis package & fail-open

**Choice:** If Redis backends need a client, add `redis` (async) to `requirements.txt` with why-comment at step 6.4. Connection errors / timeouts on Redis MUST fail open for rate limit (existing) and skip-cache for planner cache. Explicit connect/read timeouts on Redis client. No Redis in `docker-compose` for MVP (blueprint: empty `REDIS_URL` in dev).

### D7 — Default base_lat/lng to destination center

When `PlanRequest` omits base coords, resolve destination lat/lng and use as default (blueprint). Round to 3 decimals only for cache key, not for routing precision at invoke.

### D8 — Auth on endpoints

| Endpoint | Auth |
|----------|------|
| `POST /planner/generate` | `optional_auth` |
| `GET /trips` | `require_auth` |
| `GET /trips/{id}` | `optional_auth` + ownership |
| `GET /trips/{id}/geojson` | public |
| `DELETE /trips/{id}` | `require_auth` + ownership |

### D9 — Evaluation & save ordering

Generation path MUST still record evaluation (P5 bridge already does). Trip save is separate: after successful plan (and optionally on abort with partial itinerary — **LOCKED preference:** save only when `plan_complete` / usable itinerary present; aborted empty plans do not create Trip rows). Evaluation always; Trip conditional.

### D10 — Design patterns called out in the prompt

| Module | Pattern | Meaning in P6 |
|--------|---------|----------------|
| `TripService.save_from_state` | Unit of Work | Trip + TripPlaces one transaction; rollback on partial fail |
| `RateLimiterBackend` / `CacheBackend` | Strategy + Protocol | In-memory ↔ Redis via settings |
| `PlannerService` + router Queue | Ports & Adapters | HTTP/SSE adapter over HTTP-agnostic service |
| `OsrmRoutingProvider` | Adapter (P4) | Unchanged; Fake in tests |
| `core/llm/client.py` | Gateway | `LLM_MODEL` swap = zero code change |
| Destinations search / readiness | Cache-Aside (existing) | Mirror for planner cache |
| Ownership checks | Policy / Guard | Guest session match ≡ user ownership |

### D11 — Prompt build order (locked)

```
6.1 trips repository + service (save_from_state, ownership, schemas)
  → 6.2 planner router SSE generate (floor, queue, disconnect, optional_auth, auto-save hook)
    → 6.3 trips router CRUD + GeoJSON
      → 6.4 Redis rate limiter + CacheBackend planner cache
        → 6.5 backend ship checklist + pytest/smoke + context.md
```

### D12 — Verification bar

Every code step: import/unit proof. Phase closeout: API tests + `curl -N` SSE smoke + GeoJSON paste check + rate-limit 429 + cache second-hit + import guards (litellm / travel_engine purity / no redis imports outside backend module). Failures: non-zero exit + clear section headers.

### D13 — Forward locks (design-only — do not implement in P6)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Edit/replan HTTP API | P7 |
| F2 | `record_edit` + `user_edited` linkage | P7 |
| F3 | Daily LLM spend caps | post-MVP |
| F4 | Multi-worker sticky sessions / shared SSE | not required — Redis rate/cache is the multi-worker concern |

## Risks / Trade-offs

- [Risk] Doc drift if blueprint edits without step6 update → Mitigation: step6 cites blueprint P6 anchors; context points agents at step6 for build.
- [Risk] Holding generate await before streaming → Mitigation: D2 background task + Queue mandatory in Decision Log.
- [Risk] Orphan Trip without places → Mitigation: D4 single transaction + rollback tests.
- [Risk] Guest session fixation / IDOR → Mitigation: exact `wandr_session` match → 403; never skip ownership on optional_auth routes.
- [Risk] Redis outage takes down planning → Mitigation: fail-open rate limit + skip-cache; generation continues.
- [Risk] Cache returns stale prefs nuance → Mitigation: documented MVP tradeoff at parsed-preference key; TTL 1h.
- [Risk] Starting P6 before P5.12–5.14 done → Mitigation: prerequisites gate in step6 header; refuse apply if service bridge missing.
- [Risk] Over-process OpenSpec per micro-step → Mitigation: D0 batched applies.
- [Trade-off] Auto-save guests creates more Trip rows → Accepted (trip_id in SSE final event improves UX); soft-delete available.
- [Trade-off] GeoJSON public may leak trip structure by UUID → Accepted for MVP (blueprint public); no listing without auth.

## Migration Plan

1. Apply this change: write hardened `docs/steps/step6.md` (+ keep OpenSpec artifacts coherent).
2. Archive `design-p6-planner-api-persistence`.
3. Ensure P5 ship criteria green; update `context.md` Next → P6.1 if not already.
4. Implement from the prompt in batched OpenSpec applies (clusters in D0).
5. After 6.5 pass: update `docs/context.md`; register live endpoints; refresh developer manual if cadence hit (phase end).
6. Rollback of code later: unregister routers; revert trips service/repo; leave models/migrations intact; Redis optional.

## Open Questions

None blocking for authoring the prompt. Defaults above (D0–D13) are locked for `step6.md` unless the user overrides before apply.

**Resolved by lock (no either/or in prompt):**

- Absolute min-places HTTP status → **409** + `destination_not_ready`
- Guest trips → **auto-save** with `user_id=None` + `session_id`
- Ownership miss → **403** (not 404)
- Cache/rate backends → **Protocol + factory from REDIS_URL**
- SSE → **router Queue + background `generate`**, service stays callback-based
