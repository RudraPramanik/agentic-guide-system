# Wandr — P6 Cursor Prompts: Planner API + Persistence (v2 — hardened)
> **Merged into [`docs/steps/step6.md`](step6.md)** via OpenSpec change `harden-p6-planner-api-v2`
> (kept for provenance; implement from `step6.md` only — that file also locks the MVP cache key).
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P6 (3 days · 5 blueprint steps, expanded here to **6.0–6.6**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Supersedes** the prior P6 draft. **v2 changelog:** closes a polyline gap that's been invisible
> since P4 (nothing anywhere in the pipeline ever computes route geometry, yet `TripPlace.polyline`
> and the whole point of `GET /trips/{id}/geojson` depend on one existing), fixes a double/ambiguous
> `itinerary_done` emission, adds reverse-proxy streaming headers (a near-certain production
> incident on the project's stated self-hosted deployment target if left unaddressed), makes
> cache hits still persist a trip, and restores the anonymous-trip-claim flow the root blueprint
> explicitly promises but the prior draft quietly downgraded to "optional."
>
> **Layering (do not confuse):**
> - `docs/blueprint_final.md` = product / architecture source of truth
> - **this file** = Cursor build contract (sub-steps, failure boundaries, ✅ validation, tests)
> - OpenSpec = propose → apply → archive for **batched** implementation clusters
>
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current
> ✅ validation passes. Step 6.0 touches P4/P5 files — do it first, it's small, and P6.1/6.3
> cannot honestly implement GeoJSON without it.

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | No `RoutingProvider` method ever produces route geometry — `TripPlace.polyline` and `GET /geojson` render points with no connecting line | Step 6.0: `RoutingProvider.route_polyline()` (new, O(n) reuse of existing single-pair `get_route`, not a new OSRM call type); wired through `route_optimizer` → `TravelState.route` → `save_from_state` |
| 2 | Router forwards the service's raw `itinerary_done` (no `trip_id`) or emits a second one after saving — client sees either no link to the saved trip or two terminal events | Router **buffers** the terminal event, waits for the task's final state, saves the trip, yields exactly **one** enriched `itinerary_done` |
| 3 | Reverse proxy (nginx, likely on the project's Oracle Cloud target) buffers the SSE response by default → works in dev, appears frozen in prod | `Cache-Control: no-cache` + `X-Accel-Buffering: no` on the `StreamingResponse`; documented proxy config note |
| 4 | Cache hit skips persistence too → cached itineraries have no `trip_id`, can't be saved/revisited | Cache skips only the **tool loop**; `save_from_state` still runs on every cache hit |
| 5 | "Anonymous trips claimable after login" (stated in the root blueprint) silently downgraded to "optional, no route" | Restored: `POST /api/v1/trips/{id}/claim` |
| 6 | `save_from_state`'s mapping from `state.schedule`/`state.route` into `TripPlace` columns left to be inferred | Exact field-by-field mapping specified in step 6.1 |
| 7 | SSE polling loop's wait mechanism elided ("wait briefly...") → risk of busy-loop or blocked disconnect checks | `asyncio.wait_for(queue.get(), timeout=1.0)` locked exactly |
| 8 | Cached value shape unspecified — if it's only a display-rendered blob, cache hits can't feed fix #4's persistence | Cache stores a JSON-serializable subset of `TravelState` sufficient for **both** display and `save_from_state` |
| 9 | `PlanRequest` silently drops the blueprint's `accommodation_label` field | Restored (display-only, unchanged elsewhere) |
| 10 | `DELETE require_auth` vs `GET optional_auth+ownership` looks like an accidental asymmetry | Documented as intentional: no anonymous destructive actions |
| 11 | Frontend can't use native `EventSource` against a `POST` endpoint | Documented in `docs/context.md`: frontend must use `fetch()` + manual stream parsing, not `EventSource` |

---

## Step 6.0 — Cross-phase patch: route geometry (touches P4 + P5 files)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close the polyline gap. Nothing built in P4 or P5 ever computes route geometry — only
travel TIME/distance (via travel_matrix). TripPlace.polyline and GeoJSON both depend on one
existing. This is a small, surgical addition — NOT a new OSRM endpoint type, NOT O(n²) calls.
This is step 6.0. No new packages. No changes to geo/osrm.py's existing get_route() signature —
it already accepts a multi-waypoint list and already returns encoded_polyline; we're just
calling it a few more times, in the right place, and threading the result through.

─── EXTEND src/travel_engine/protocols.py (P4 file) ───

  class RoutingProvider(Protocol):
      async def travel_matrix(self, waypoints: list[tuple[UUID, float, float]]) -> list[RouteLeg]: ...

      async def route_polyline(self, waypoints: list[tuple[float, float]]) -> str | None:
          """
          NEW. Encoded polyline for a route through the given waypoints, IN ORDER (2+ points).
          Returns None if unavailable (provider fell back to haversine — no real road geometry
          exists to draw). Never raises. Used AFTER route_optimizer has already picked the
          winning stop order — this is not part of the O(n) travel_matrix optimization step.
          """
          ...

─── EXTEND src/planner/routing_provider.py (P4 file) — OsrmRoutingProvider ───

  async def route_polyline(self, waypoints: list[tuple[float, float]]) -> str | None:
      """Thin wrapper over the EXISTING geo.osrm.get_route() — no new OSRM call type."""
      result = await get_route(waypoints)
      return result.encoded_polyline if not result.fallback_used else None

─── EXTEND tests/travel_engine FakeRoutingProvider (P4 test support) ───

  Add a deterministic route_polyline() returning a fixed placeholder string (e.g. "fake_polyline")
  so P4/P5 tests that already use FakeRoutingProvider keep working unchanged.

─── EXTEND src/travel_engine/route_optimizer.py (P4 file) — OptimizeResult + optimize_route ───

  class OptimizeResult(BaseModel):
      ordered: list[ScoredPlace]
      legs: list[RouteLeg]
      total_travel_min: int
      dropped_stops: list[DroppedStop] = Field(default_factory=list)
      still_over_budget: bool = False
      leg_polylines: list[str | None] = Field(default_factory=list)   # NEW — aligned to `ordered`;
                                                                        # index i = polyline INTO
                                                                        # ordered[i] (from the
                                                                        # previous stop, or base
                                                                        # for i=0)
      day_polyline: str | None = None                                  # NEW — aggregate, whole day

  # After the winning permutation is chosen (existing logic unchanged), ADD:
  #   waypoints_final = [(base_lat, base_lng)] + [(sp.place.lat, sp.place.lng) for sp in ordered]
  #   leg_polylines = []
  #   for i in range(len(ordered)):
  #       leg = await routing.route_polyline(waypoints_final[i:i+2])   # 2-point call, reuses
  #       leg_polylines.append(leg)                                    # existing get_route()
  #   day_polyline = await routing.route_polyline(waypoints_final)     # ONE more call, full list
  #
  # Total added calls per day: N (legs) + 1 (aggregate) = at most 7 for MAX_PLACES_PER_DAY=6 —
  # down from the original O(n^2)=42 bug this replaces, and using 100% existing, already-tested
  # P2 code. Do NOT add a new geo/osrm.py function — route_polyline() is purely a thin adapter
  # wrapper, the actual HTTP call is unchanged get_route().

─── CLARIFY src/planner/graph/state.py TravelState shape (P5 file — was left loosely typed) ───

  TravelState.schedule is a list of per-day dicts with this shape (document it explicitly —
  this was never pinned down precisely in P5 and P6 needs it to be):

    {
      "day": int,
      "stops": [
        {
          "place_id": str, "name": str, "lat": float, "lng": float, "category": str,
          "order": int, "travel_time_min": int, "visit_duration_min": int,
          "suggested_start_time": str, "arrival_note": str | None,
          "leg_polyline": str | None,        # from OptimizeResult.leg_polylines[i]
        },
        ...
      ],
      "total_distance_km": float,
      "total_travel_min": int,
      "day_polyline": str | None,             # from OptimizeResult.day_polyline
    }

  build_route / build_schedule tools (P5) must populate leg_polyline / day_polyline from
  OptimizeResult onto this shape — if those tools currently discard OptimizeResult's polyline
  fields, add the two lines that carry them over. This is a completion of P5's tool bodies,
  not a redesign.

─── RULES ───
- travel_engine stays pure — route_optimizer calls routing.route_polyline() via the SAME
  Protocol DI pattern already used for travel_matrix(); this is not a new I/O boundary, just
  a new method on the same injected interface.
- A day where routing fell back to haversine (no OSRM) simply has polyline=None everywhere for
  that day — GeoJSON renders points with no line for that day only. This degrades gracefully,
  consistent with every other OSRM-down fallback in this codebase; it must NOT raise or block
  itinerary generation.

─── FAILURE BOUNDARY ───
route_polyline() failure → None, never raises. A day with all-None polylines still produces a
valid (if line-less) GeoJSON FeatureCollection — never a 500.

─── VALIDATION ───
  python -c "
import asyncio
from uuid import uuid4
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.route_optimizer import optimize_route

class FakeWithPolyline:
    async def travel_matrix(self, waypoints):
        from src.travel_engine.protocols import RouteLeg
        ids = [w[0] for w in waypoints]
        return [RouteLeg(from_place_id=a, to_place_id=b, duration_min=10, distance_km=1.0)
                for a in ids for b in ids if a != b]
    async def route_polyline(self, waypoints):
        return f'poly_{len(waypoints)}pts'

async def main():
    places = [ScoredPlace(place=PlaceCandidate(id=uuid4(), name=n, category='attraction',
              enriched_tags=[], lat=0.0, lng=0.0), score=1.0, score_breakdown={}) for n in ('A','B','C')]
    result = await optimize_route(places, 0.0, 0.0, FakeWithPolyline())
    assert len(result.leg_polylines) == 3
    assert all(p is not None for p in result.leg_polylines)
    assert result.day_polyline == 'poly_4pts'   # base + 3 stops
    print('PASS — 6.0 polyline threading through route_optimizer')

asyncio.run(main())
"

✅ Failure path: mock route_polyline to return None (simulating OSRM fallback) — assert
   result.leg_polylines are all None and result.day_polyline is None, no exception raised.
```

---

## Prerequisites (P5 must be complete; Step 6.0 above must land first)

- `docs/context.md` shows P5.1–5.14 ✅ and Next step → P6.1
- Step 6.0 (above) applied and its validation passing — `RoutingProvider.route_polyline()` real
- `PlannerService.generate` real (`wait_for`, `on_event`, fresh `ToolContext` via `config["configurable"]`)
- `python -m pytest tests/ -v` green including P5 suite
- Trip / TripPlace / TripEditEvent **models** exist (P1); trips repo/service/router/schemas still stubs
- `RateLimiterBackend` + `InMemoryRateLimiter` + path table exist (P1/P2); Redis backend not wired yet
- `REDIS_URL` in settings (may be `""`); `PLANNER_ABSOLUTE_MIN_PLACES` not yet in settings — add in 6.2
- Cookie name **`wandr_session`** already used in `src/auth/router.py`

**Already real (do NOT reinvent):**
- `src/planner/service.py`, `src/planner/graph/*`, `src/core/middleware/rate_limit.py`,
  `src/core/llm/client.py`, `src/planner/routing_provider.py`, `src/trips/models.py`,
  `Destination.lat/lng/place_count`

**Current stubs:**
- `src/trips/{repository,service,router,schemas,exceptions}.py`
- `src/planner/{router,schemas}.py` (service real; HTTP is not)
- Redis rate limiter / any `CacheBackend`

## Prompt conventions

- **Extend, don't replace** existing code unless the step explicitly says replace.
- **Layering:** Router → Service → Repository only. Routers never touch DB or Redis clients directly.
- **LLM/Geo rules:** unchanged from P0–P5 (only via `core/llm/client.py` / `src/geo/`).
- **Env:** all via `get_settings()`.
- **Envelopes:** `ApiResponse[T]` / `PaginatedResponse[T]` / `ErrorResponse` for JSON; SSE is
  its own frame format, not `ApiResponse`.
- **Time:** `datetime.now(timezone.utc)`; schedule times stay naive `"HH:MM"`.
- **No new packages** without `requirements.txt` + why-comment. Expected: `redis` at 6.4.
- **Failure standards:** every code prompt has `─── FAILURE BOUNDARY ───` and `✅ Failure path:`.
- **OpenSpec cadence:** batch `6.0`, `6.1`, `6.2`, `6.3`, `6.4–6.5`.

---

## P6 architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    P6 dependency graph (canonical order)                     │
└──────────────────────────────────────────────────────────────────────────────┘

  6.0 route_polyline (P4/P5 patch — geometry gap closed)
        │
  6.1 trips repository + TripService.save_from_state + ownership + claim + schemas
        │
  6.2 planner/schemas + POST /planner/generate SSE
        │   (floor check → queue+task → buffer terminal event → save → ONE itinerary_done)
        │
  6.3 trips/router CRUD + GeoJSON + claim endpoint
        │
  6.4 Redis RateLimiterBackend + CacheBackend (cache hits still persist)
        │
  6.5 ship checklist + pytest/smoke + context.md

  Abstraction / DI map:

    FastAPI Router
      ├─► PlannerService.generate(on_event=...)     # HTTP-agnostic (P5)
      │     └─► graph + ToolContext.routing: RoutingProvider (now incl. route_polyline)
      ├─► TripService → TripRepository              # UoW save / ownership / claim
      └─► CacheBackend (Protocol)                   # InMemory | Redis

    RateLimitMiddleware → RateLimiterBackend (Protocol)   # InMemory | Redis
    LLM (unchanged) → core/llm/client.py ← LLM_MODEL env
    Geo (unchanged) → src/geo/* gateways
```

**Canonical build order:**
```
6.0 → 6.1 → 6.2 → 6.3 → 6.4 → 6.5
```

**SSE shape (LOCKED, v2):**
```
Client ──POST /api/v1/planner/generate──► Router
  1) optional_auth + ensure wandr_session
  2) load destination; place_count < PLANNER_ABSOLUTE_MIN_PLACES → 409
  3) default base_lat/lng ← destination.lat/lng when omitted
  4) cache lookup (6.4) — hit: SKIP TOOL LOOP ONLY, still runs save_from_state
  5) queue = asyncio.Queue(); on_event = enqueue
  6) task = asyncio.create_task(PlannerService.generate(..., on_event=on_event))
  7) loop: asyncio.wait_for(queue.get(), timeout=1.0); disconnect → task.cancel()
     - non-terminal events (tool_started/tool_done/phase_changed/validation_done) → yield immediately
     - terminal events (itinerary_done/error/clarification_needed) → BUFFER, do not yield yet
  8) once task is done: if buffered terminal was itinerary_done AND state usable →
     save_from_state → enrich payload with trip_id → yield the ONE final frame
  9) StreamingResponse with Cache-Control: no-cache, X-Accel-Buffering: no
```

---

## P6 design decisions (locked)

### Guest ownership + claim — LOCKED

- Cookie: `wandr_session`.
- Unauthenticated get/delete (where allowed): cookie value MUST equal `Trip.session_id`. Mismatch/missing → **403**, never 404.
- Authenticated: `Trip.user_id` must match current user, OR (new, restored) the trip is
  claimable via `POST /trips/{id}/claim` if `Trip.user_id IS NULL` and the session cookie
  matches — this is the "anonymous trips claimable after login" behavior the root blueprint
  explicitly promises. It was NOT optional; it's restored here as a real endpoint.
- `DELETE` requires full auth (`require_auth`) even though `GET` allows guest ownership access
  — **intentional**: no anonymous destructive actions. State this in code comments, not just
  this doc, so it doesn't read as an accidental asymmetry to a future maintainer.

### Absolute min-places floor — LOCKED (unchanged from prior draft)

- `PLANNER_ABSOLUTE_MIN_PLACES: int = 10`, checked before any graph/cache work, HTTP 409
  `destination_not_ready`. Soft `PLANNER_MIN_READINESS_SCORE` stays in-graph warning only.

### `itinerary_done` — LOCKED (v2, fixes the ambiguity)

The router NEVER forwards the service's raw terminal event immediately. It buffers whichever
terminal event fires (`itinerary_done` / `error` / `clarification_needed`), waits for the
background task to fully complete, performs trip-save post-processing if applicable, and yields
**exactly one** enriched terminal frame as the true last event of the stream. Two terminal
frames, or a terminal frame missing `trip_id` when a trip was actually saved, are both bugs.

### Cache hit still persists — LOCKED (v2)

A cache hit skips the tool loop (the expensive part) — it does NOT skip `save_from_state`. The
cached value (see below) must carry enough of a state-shape to feed persistence, not just a
pretty rendered itinerary for display.

### Cached value shape — LOCKED (v2)

Cache stores a JSON-serializable subset of the final `TravelState` — specifically `schedule`
(with `leg_polyline`/`day_polyline` per step 6.0), `itinerary` (narrative), and the parsed
preference fields — sufficient to both render the SSE response AND call `save_from_state`
identically to the non-cached path. It is not a narrative-only blob.

```
key = sha256(
  f"{destination_id}:{','.join(sorted(interests))}:{days}:{budget}:"
  f"{round(base_lat, 3)}:{round(base_lng, 3)}"
)
TTL = PLANNER_CACHE_TTL_SECONDS (default 3600)
```

### Trip save (UoW) — LOCKED, field mapping now explicit (v2)

`save_from_state(state, user_id, session_id) → Trip`, one transaction:

```
Trip.days              = len(state["schedule"])
Trip.preferences        = {"interests": state["interests"], "budget": state["budget"],
                            "include_offbeat": state["include_offbeat"],
                            "include_trekking": state["include_trekking"]}
Trip.status             = COMPLETE if state["plan_complete"] and not state["abort_triggered"]
                           else (FAILED if state["abort_triggered"] else DRAFT)
Trip.user_id            = user_id (nullable — guests get None)
Trip.session_id         = session_id
Trip.destination_id     = state["destination_id"]

for day in state["schedule"]:
    for stop in day["stops"]:
        TripPlace(
            trip_id=trip.id, place_id=stop["place_id"], day_number=day["day"],
            order_in_day=stop["order"], travel_time_min=stop["travel_time_min"],
            visit_duration_min=stop["visit_duration_min"],
            suggested_start_time=stop["suggested_start_time"],
            arrival_note=stop.get("arrival_note"),
            polyline=stop.get("leg_polyline"),   # per-stop leg geometry, from step 6.0
        )
```

Do NOT create a Trip row for an empty abort or clarification-only generation with no schedule.
Evaluation (P5) is always written independently of whether a Trip gets saved.

### SSE events — LOCKED (unchanged names)

```
preferences_done | phase_changed | tool_started | tool_done
validation_done | itinerary_done | clarification_needed | error
```

### Reverse-proxy streaming — LOCKED (v2, new)

`StreamingResponse` for `/planner/generate` MUST set:
```python
headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
```
Document in `docs/context.md`'s deployment notes: any reverse proxy in front of this route
(nginx, Caddy, etc.) MUST have response buffering disabled for this path
(`proxy_buffering off;` for nginx), or the stream will silently arrive all-at-once in
production despite working correctly against `uvicorn` directly in dev. This is worth stating
plainly given the project's self-hosted deployment target almost certainly involves a
reverse proxy.

### Frontend integration note — LOCKED (v2, doc-only, no backend code)

`/planner/generate` is `POST`, so the frontend CANNOT use the browser's native `EventSource`
(GET-only) to consume it — it must use `fetch()` with a manual `ReadableStream` reader parsing
SSE frames. Record this in `docs/context.md` so it isn't discovered as a frontend integration
surprise later.

### Auth matrix — LOCKED

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/planner/generate` | `optional_auth` |
| GET | `/api/v1/trips` | `require_auth` |
| GET | `/api/v1/trips/{id}` | `optional_auth` + ownership |
| GET | `/api/v1/trips/{id}/geojson` | public |
| DELETE | `/api/v1/trips/{id}` | `require_auth` + ownership |
| POST | `/api/v1/trips/{id}/claim` | `require_auth` + session-match + `user_id IS NULL` |

### Abstraction & provider swap — LOCKED (unchanged)

| Concern | Protocol | Dev | Prod | Swap mechanism |
|---|---|---|---|---|
| Rate limit | `RateLimiterBackend` | `InMemoryRateLimiter` | `RedisRateLimiter` | `get_rate_limiter()` |
| Planner cache | `CacheBackend` | `InMemoryCacheBackend` | `RedisCacheBackend` | `get_cache_backend()` |
| Routing (incl. geometry) | `RoutingProvider` | Fake / OSRM | OSRM | ToolContext DI |
| LLM | `chat_*` | any litellm model | same | `LLM_MODEL` env |

Routers and domain services MUST NOT `import redis` — only backend modules under `src/core/`.

### Design patterns

| Module | Pattern | Meaning |
|---|---|---|
| `TripService.save_from_state` | Unit of Work | Trip + places, one transaction |
| `RateLimiterBackend` / `CacheBackend` | Strategy + Protocol | In-memory ↔ Redis via settings |
| Planner router + Queue | Ports & Adapters | SSE adapter over HTTP-agnostic service |
| `RoutingProvider.route_polyline` | Adapter (P4, extended 6.0) | Geometry, same DI as travel_matrix |
| Ownership + claim helper | Policy / Guard | Guest session ≡ ownership; claim = ownership transfer |

### Forward locks (design-only — do not implement in P6)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Edit/replan HTTP API | P7 |
| F2 | `record_edit` + `user_edited` on evaluation | P7 |
| F3 | Daily LLM spend caps | post-MVP |
| F4 | Redis in docker-compose / multi-region | not required for MVP |

---

## Step 6.1 — trips/ repository + service (save_from_state + ownership + claim)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: TripRepository + TripService persistence, ownership, and the restored claim flow.
This is step 6.1. No FastAPI planner generate yet. No Redis. No new packages.

─── IMPLEMENT ───

  src/trips/exceptions.py
    - TripNotFoundError (404), TripForbiddenError (403), TripAlreadyClaimedError (409 —
      NEW: raised by claim_for_user when trip.user_id is already set)

  src/trips/schemas.py
    - TripOut, TripPlaceOut — include suggested_start_time, visit_duration_min, polyline,
      lat/lng when joined. No invented columns.

  src/trips/repository.py
    - class TripRepository(BaseRepository[Trip, UUID])
    - list_by_user(user_id, params) / list_by_session(session_id, params)
    - get_with_places(trip_id) — eager load TripPlace (+ Place coords for GeoJSON)

  src/trips/service.py
    - save_from_state(state, user_id, session_id) → Trip
        Exact field mapping per the LOCKED design decision above. Single transaction:
        create Trip, insert all TripPlace rows in order, commit. Rollback on any failure —
        never leave a Trip row without its places.
        Returns None (no Trip created) if state["schedule"] is empty or
        state["plan_complete"] is False and state["abort_triggered"] is False and there's
        genuinely nothing usable (clarification-only case).
    - assert_can_access(trip, *, user_id, session_id) → None
        Guest (user_id is None): session_id must equal trip.session_id, else TripForbiddenError.
        Authenticated: trip.user_id == user_id, else TripForbiddenError — UNLESS trip.user_id
        is None and session_id matches trip.session_id (still accessible pre-claim by the
        original guest session), consistent with claim semantics below.
    - claim_for_user(trip, user_id, session_id) → Trip                      # RESTORED (v2)
        Preconditions: trip.user_id is None (else TripAlreadyClaimedError) AND
        session_id == trip.session_id (else TripForbiddenError).
        Sets trip.user_id = user_id; commits; returns updated trip.

─── RULES ───
- Router optional in 6.1; service must be unit-testable with db_session directly.
- Do not call PlannerService from trips service.
- Repository flush-only; service owns the commit boundary (matches AuthService precedent).

─── FAILURE BOUNDARY ───
Partial TripPlace insert → full rollback, never an orphan Trip.
Ownership miss → TripForbiddenError (403), never 404.
Claim on an already-claimed trip → TripAlreadyClaimedError (409), never a silent no-op.

─── VALIDATION ───
  python -c "
from src.trips.repository import TripRepository
from src.trips.service import TripService
assert hasattr(TripService, 'save_from_state')
assert hasattr(TripService, 'claim_for_user')
print('PASS — 6.1 trips service/repo surface, including restored claim_for_user')
"

  # tests/trips/test_save_from_state.py (land with 6.5):
  #   save → get_with_places returns all stops with polyline populated (from step 6.0 data)
  #   forced mid-insert fail → zero committed trips
  #   claim: guest session matches, trip.user_id None → succeeds; wrong session → 403;
  #          already-claimed → 409

✅ Failure path: simulated place-insert failure → zero committed trips for that attempt.
✅ Failure path: claim with mismatched session → TripForbiddenError, trip.user_id unchanged.
```

---

## Step 6.2 — planner/router.py — POST /generate streaming SSE (v2 rewrite)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: HTTP SSE adapter over PlannerService.generate, with the terminal-event buffering fix,
proxy-buffering headers, and the absolute min-places floor. This is step 6.2.

─── UPDATE src/config.py ───

  PLANNER_ABSOLUTE_MIN_PLACES: int = 10
  PLANNER_CACHE_TTL_SECONDS: int = 3600   # used from 6.4, declared now

─── IMPLEMENT src/planner/schemas.py ───

  class PlanRequest(BaseModel):
      destination_id: UUID
      raw_input: str
      days: int | None = None
      base_lat: float | None = None
      base_lng: float | None = None
      accommodation_label: str | None = None   # RESTORED (v2) — display-only, per blueprint

─── IMPLEMENT src/planner/router.py ───

  router = APIRouter(prefix="/api/v1/planner", tags=["planner"])

  TERMINAL_EVENTS = {"itinerary_done", "error", "clarification_needed"}

  @router.post("/generate")
  async def generate_plan(
      body: PlanRequest,
      request: Request,
      payload: TokenPayload | None = Depends(optional_auth),
      db: AsyncSession = Depends(get_db),
  ):
      # 1. Resolve session_id (reuse the same wandr_session cookie pattern as auth router)
      session_id = request.cookies.get("wandr_session") or str(uuid.uuid4())

      # 2. Resolve destination; 404 if missing
      dest = await DestinationService(db).get_by_id(body.destination_id)

      # 3. LOCKED floor check — BEFORE any graph or cache work
      if dest.place_count < get_settings().PLANNER_ABSOLUTE_MIN_PLACES:
          raise DestinationNotReadyError(place_count=dest.place_count)   # → 409

      base_lat = body.base_lat if body.base_lat is not None else dest.lat
      base_lng = body.base_lng if body.base_lng is not None else dest.lng
      user_id = payload.user_id if payload else None

      async def event_gen():
          queue: asyncio.Queue = asyncio.Queue()

          def on_event(event: str, data: dict):
              queue.put_nowait((event, data))

          # 4. Cache lookup (6.4 wires this; 6.2 may call a no-op checker that always misses)
          cached_state = await maybe_get_cached_state(body, base_lat, base_lng)

          if cached_state is not None:
              task = asyncio.create_task(_replay_cached(cached_state, on_event))
          else:
              task = asyncio.create_task(
                  PlannerService().generate(
                      destination_id=body.destination_id, raw_input=body.raw_input,
                      base_lat=base_lat, base_lng=base_lng, session_id=session_id,
                      on_event=on_event,
                  )
              )

          pending_terminal: tuple[str, dict] | None = None
          try:
              while True:
                  if await request.is_disconnected():
                      task.cancel()
                      break
                  try:
                      event, data = await asyncio.wait_for(queue.get(), timeout=1.0)
                  except asyncio.TimeoutError:
                      if task.done() and queue.empty():
                          break
                      continue
                  if event in TERMINAL_EVENTS:
                      pending_terminal = (event, data)   # LOCKED — buffer, don't yield yet
                      continue
                  yield sse_frame(event, data)

              if pending_terminal:
                  event, data = pending_terminal
                  if event == "itinerary_done":
                      try:
                          final_state = task.result()
                      except Exception:
                          final_state = None
                      if final_state is not None:
                          trip = await TripService(db).save_from_state(
                              final_state, user_id=user_id, session_id=session_id,
                          )
                          if trip is not None:
                              data = {**data, "trip_id": str(trip.id)}
                  yield sse_frame(event, data)
          finally:
              if not task.done():
                  task.cancel()

      response = StreamingResponse(event_gen(), media_type="text/event-stream")
      response.headers["Cache-Control"] = "no-cache"
      response.headers["X-Accel-Buffering"] = "no"   # LOCKED — disables nginx buffering
      response.headers["Connection"] = "keep-alive"
      response.set_cookie("wandr_session", session_id, httponly=False, samesite="lax", max_age=30*24*3600)
      return response

─── REGISTER ───

  main.py: app.include_router(planner_router)

─── RULES ───
- `save_from_state` runs for BOTH the fresh-generation path AND the cache-hit path (via
  `_replay_cached`, which must produce the same `final_state` shape `save_from_state` expects).
- Rate limiting for this path already exists (10/min via P1's path table) — do not add a
  second limiter here.
- `PlannerService` remains free of `StreamingResponse`/`Request` imports — this file is the
  ONLY SSE adapter.

─── FAILURE BOUNDARY ───
place_count below floor → 409, no graph, no cache lookup. Disconnect → task cancelled cleanly.
Timeout inside the service → service's own error event flows through as the buffered terminal
frame (no trip save attempted for an error/clarification terminal event).
Must NOT: forward itinerary_done before trip_id is known; must NOT: emit two terminal frames.

─── VALIDATION ───
  python -c "
from src.main import create_app
app = create_app()
paths = [getattr(r,'path',None) for r in app.routes]
assert any(p and 'planner/generate' in p for p in paths)
print('PASS — 6.2 generate route registered')
"

  Get-ChildItem -Path src\planner\service.py | Select-String "StreamingResponse|is_disconnected"
  # Expected: zero matches — service stays HTTP-agnostic

✅ Failure path: destination with place_count=0 → 409 destination_not_ready.
✅ Failure path: mock PlannerService.generate to emit itinerary_done then raise inside the
   task — assert exactly ONE terminal frame reaches the client and it has no trip_id (since
   final_state was unrecoverable), not a second error frame stacked after it.
```

---

## Step 6.3 — trips/router.py — CRUD + GeoJSON + claim

```
Read AGENT.md and docs/context.md before proceeding.

TASK: HTTP trips API, GeoJSON builder (now genuinely has geometry to render, per step 6.0),
and the restored claim endpoint. This is step 6.3.

─── IMPLEMENT TripService.build_geojson ───

  - Input: trip with places/polylines/coords already loaded via get_with_places
  - Per-day LineString features from TripPlace.polyline (present now, per step 6.0) plus
    per-stop Point features with name/order/suggested_start_time as properties
  - A day with all-None polylines (OSRM was down during generation) still produces valid
    Point features for that day — just no LineString. Document this as expected degradation,
    not a bug to chase.
  - Pure from DB fields — no live OSRM/httpx call on read.

─── IMPLEMENT src/trips/router.py ───

  GET    /api/v1/trips              → PaginatedResponse[TripOut]  (require_auth)
  GET    /api/v1/trips/{id}         → ApiResponse[TripOut]        (optional_auth + ownership)
  GET    /api/v1/trips/{id}/geojson → GeoJSON FeatureCollection   (public)
  DELETE /api/v1/trips/{id}         → 204                          (require_auth + ownership)
  POST   /api/v1/trips/{id}/claim   → ApiResponse[TripOut]         (require_auth + session +
                                                                     user_id IS NULL)          # RESTORED

  Claim handler: 403 on session mismatch (TripForbiddenError), 409 on already-claimed
  (TripAlreadyClaimedError) — both via the existing global WandrError handler, no ad-hoc
  try/except in the router.

─── RULES ───
- DELETE requires full auth even though GET allows guest ownership — intentional, no
  anonymous destructive actions (comment this in the router code, not just this doc).
- Soft-delete via BaseRepository (Trip has SoftDeleteMixin).
- Do not add P7 edit routes here.

─── FAILURE BOUNDARY ───
Wrong owner / guest session mismatch → 403. Missing trip → 404. Already-claimed → 409.
Must NOT: 500 on ownership miss; must NOT: call OSRM in geojson.

─── VALIDATION ───
  python -c "
from src.main import create_app
app = create_app()
paths = [getattr(r,'path',None) for r in app.routes]
assert any(p and 'trips' in p for p in paths)
assert any(p and 'claim' in p for p in paths)
print('PASS — 6.3 trips routes present including claim', [p for p in paths if p and 'trips' in p])
"

  # Testclient: guest generates trip (no auth) → GET geojson → LineString present for at
  # least one day (with FakeRoutingProvider returning non-None polylines in tests)
  # Guest logs in, POST /trips/{id}/claim with matching session → 200, trip.user_id set
  # Second claim attempt on same trip → 409

✅ Failure path: other user's trip → 403. Claim by non-owner session → 403. Re-claim → 409.
```

---

## Step 6.4 — Redis rate limiter + planner CacheBackend (cache hits still persist)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Swappable Redis backends behind Protocols; wire the planner cache so hits still call
save_from_state. This is step 6.4.

─── PACKAGES ───

  redis>=5,<6  # P6.4 — optional REDIS_URL backends for rate limit + planner cache; pin exact
               # version once verified during implementation, per project convention

─── IMPLEMENT CacheBackend (src/core/cache/backends.py) ───

    class CacheBackend(Protocol):
        async def get(self, key: str) -> str | None: ...
        async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    InMemoryCacheBackend
    RedisCacheBackend   # constructed only when REDIS_URL set; explicit connect/read timeouts

    def get_cache_backend() -> CacheBackend:
        settings = get_settings()
        return RedisCacheBackend(...) if settings.REDIS_URL else InMemoryCacheBackend()

  Errors on get/set → log + treat as miss / no-op set — never raise.

─── EXTEND rate_limit.py ───

  RedisRateLimiter(RateLimiterBackend) when REDIS_URL set; get_rate_limiter() selects
  InMemory vs Redis; fail-open behavior unchanged from P1.

─── WIRE planner cache (src/planner/cache.py or a service helper) ───

  async def maybe_get_cached_state(body: PlanRequest, base_lat: float, base_lng: float) -> dict | None:
      """
      Cache lookup using the LOCKED key formula (rounded coords). Requires parsed
      preferences to compute interests/days/budget for the key — since parse_preferences
      normally runs INSIDE the graph, this MVP cache check uses a lightweight heuristic
      pre-parse (or: cache key is computed AFTER parse_preferences runs once, and only the
      REMAINING tool-loop work is skipped on a hit — pick ONE, locked: compute the cache
      key from body.raw_input's hash directly for MVP simplicity, accepting a slightly
      coarser cache — document this explicitly rather than silently picking one).
      Returns a dict shaped like the relevant subset of TravelState (schedule/itinerary/
      prefs — see LOCKED cached value shape) on hit, None on miss or backend error.
      """

  async def _replay_cached(cached_state: dict, on_event: Callable) -> dict:
      """Emits preferences_done/phase_changed/itinerary_done from cached data without
      running the tool loop; returns the reconstructed final_state dict so the router's
      normal save_from_state path (step 6.2) handles persistence identically to the
      non-cached path."""

  On a successful fresh generation (plan_complete, not abort_triggered): best-effort
  `cache_backend.set(key, json.dumps(cacheable_subset), ttl)`.

─── RULES ───
- No redis imports in src/planner/router.py or src/trips/* — only via get_cache_backend /
  get_rate_limiter.
- Empty REDIS_URL → pure in-memory; docker-compose stays Redis-free for MVP.
- Cache hits go through the SAME save_from_state call as fresh generations (step 6.2's
  event_gen doesn't special-case cached vs fresh for persistence).

─── FAILURE BOUNDARY ───
Redis down → fail-open rate limit; cache treated as miss; generation continues fresh.
Must NOT: 500 on cache backend errors.

─── VALIDATION ───
  python -c "
from src.core.middleware.rate_limit import get_rate_limiter, InMemoryRateLimiter
assert isinstance(get_rate_limiter(), InMemoryRateLimiter)
print('PASS — 6.4 limiter factory, empty REDIS_URL → in-memory')
"

  Get-ChildItem -Path src\planner,src\trips -Recurse -Filter *.py |
    Select-String "import redis|from redis"
  # Expected: zero matches

  # Integration: same PlanRequest twice (same prefs/base, rounded) → second call's SSE
  # stream skips tool_started/tool_done events entirely and still yields itinerary_done
  # WITH a trip_id — assert the second response's trip_id differs from the first (a NEW
  # Trip row was created from the cached state, not a stale reference to the first trip).

✅ Failure path: mock Redis raising on both get and set → generation still succeeds
   (cache treated as a clean miss, no exception surfaces to the client).
```

---

## Step 6.5 — Backend ship checklist + pytest/smoke + context.md

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close P6 with tests, smoke, import guards, and context update. This is step 6.5.

─── TESTS ───

  tests/travel_engine/test_route_optimizer_polyline.py  — step 6.0 regression (leg_polylines
    aligned to ordered stops; day_polyline present; None-on-fallback degrades cleanly)
  tests/trips/ — save_from_state UoW + polyline persisted, ownership 403, claim 200/403/409,
                 geojson has LineString when polylines present
  tests/planner/ — generate 409 floor, single terminal-event regression (mock a service that
                   fires itinerary_done then a spurious second event — assert client sees ONE
                   terminal frame), disconnect cancel, cache hit still persists a NEW trip_id
  tests/core/ — Redis limiter/cache selection + fail-open (mocked)

─── SMOKE ───

  scripts/test_p6_smoke.py:
    1) destinations/search + readiness + places page (sanity, from P2/P3)
    2) curl -N POST /api/v1/planner/generate → tool_started/tool_done stream live, THEN
       exactly one itinerary_done with trip_id
    3) GET trip geojson → at least one LineString feature (FakeRoutingProvider/live OSRM)
    4) second identical generate → fast cache path, NEW trip_id, no tool_started events
    5) POST /trips/{id}/claim (after a mock login) → 200, then re-claim → 409
    6) import guards (redis / StreamingResponse-in-service / litellm scope)

─── UPDATE docs/context.md (ONLY after green) ───

  - Last updated / Next step → P7.1
  - Progress 6.0–6.5 ✅
  - Implemented modules: trips repo/service/router (incl. claim), planner HTTP SSE, cache
    backends, route_polyline geometry threading
  - Live endpoints: POST /planner/generate, trips CRUD + geojson + claim
  - Deployment note: reverse proxy MUST disable response buffering for /planner/generate
    (nginx: `proxy_buffering off;` for this location)
  - Frontend note: /planner/generate is POST — frontend must use fetch() + manual SSE
    parsing, NOT the native EventSource API
  - Stubs: remove trips/planner HTTP stubs; keep P7 edit ops as stubs
  - Do NOT claim P7 complete

─── FAILURE BOUNDARY ───
Any checklist miss → do not mark P6 done in context.md.

─── VALIDATION ───
  python -m pytest tests/ -v
  python scripts/test_p6_smoke.py

✅ Failure path: failing pytest or smoke blocks the context.md P6-complete update.
```

---

## P6 Complete — Full Verification Checklist

```bash
python -m pytest tests/ -v
python scripts/test_p6_smoke.py

python -c "from src.main import create_app; app=create_app(); paths=[getattr(r,'path',None) for r in app.routes]; assert any(p and 'planner/generate' in p for p in paths); assert any(p and 'claim' in p for p in paths); print('routes ok')"

Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "import litellm|from litellm" | Where-Object { $_.Path -notmatch "core\\llm\\client\.py" }
# Expected: zero matches

Get-ChildItem -Path src\travel_engine -Recurse -Filter *.py | Select-String "src\.geo|import httpx|litellm|qdrant"
# Expected: zero matches

Get-ChildItem -Path src\planner\router.py,src\trips -Recurse -Filter *.py | Select-String "import redis|from redis"
# Expected: zero matches

Get-ChildItem -Path src\planner\service.py | Select-String "StreamingResponse|is_disconnected"
# Expected: zero matches

echo "P6 COMPLETE — proceed to P7"
```

### P6 ship criteria (v2)

| Check | Expected |
|-------|----------|
| Route geometry | `TripPlace.polyline` populated; GeoJSON has LineString features |
| Trip UoW | Save + get_with_places; rollback on partial fail |
| Guest ownership | Session mismatch → 403 |
| Claim flow | Restored: 200 on valid claim, 403 wrong session, 409 already-claimed |
| SSE generate | Streaming while running; exactly ONE terminal frame, always with trip_id when saved |
| Proxy headers | `Cache-Control: no-cache`, `X-Accel-Buffering: no` present |
| Absolute min places | 409 before graph or cache |
| Cache hits | Still call save_from_state; produce a new, distinct trip_id |
| Service purity | No StreamingResponse in planner/service.py |
| Protocol backends | REDIS_URL selects Redis; empty → in-memory; fail-open on Redis errors |
| Import guards | litellm / travel_engine / redis / tool-impl all clean |
| pytest + smoke | Green; context.md updated only after |
| P7 edits | Not registered |

### Recommended OpenSpec implementation batches

1. `6.0` — cross-phase polyline patch (P4/P5 files)
2. `6.1` — trips repository + save_from_state + ownership + claim + schemas
3. `6.2` — planner SSE router with terminal-event buffering + proxy headers + floor check
4. `6.3` — trips CRUD + GeoJSON + claim endpoint
5. `6.4–6.5` — Redis backends + cache-persists-trip + tests/smoke + context.md