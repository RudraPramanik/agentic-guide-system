# Wandr — P6 Cursor Prompts: Planner API + Persistence
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P6 (3 days · 5 blueprint steps **6.1–6.5**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Layering (do not confuse):**
> - `docs/blueprint_final.md` = product / architecture source of truth
> - **this file** = Cursor build contract (sub-steps, failure boundaries, ✅ validation, tests)
> - OpenSpec = propose → apply → archive for **batched** implementation clusters (not one ceremony per micro-step)
>
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current ✅ validation passes.
>
> Implement **from this prompt only**. Do not invent edit/replan HTTP (P7), dual graph invoke paths, or Redis imports in routers.

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | Await full `generate` then dump buffered SSE → no live events; disconnect cannot cancel | Background task + `asyncio.Queue` + yield while running; `request.is_disconnected()` → cancel task |
| 2 | `StreamingResponse` / `Request` inside `PlannerService` → HTTP coupling; breaks P5 callback tests | Service stays `on_event` callback only; **router** is the SSE adapter |
| 3 | Guest ownership returns 404 → ambiguous vs missing trip | Guest: `wandr_session` **exact match** `Trip.session_id` else **403** (same as user IDOR) |
| 4 | Trip row commits then TripPlace fails → orphan trip | Unit of Work: Trip + TripPlaces **one transaction**; full rollback on any failure |
| 5 | Absolute min-places checked after graph start → wasted LLM spend | Pre-graph HTTP **409** `destination_not_ready` when `place_count < PLANNER_ABSOLUTE_MIN_PLACES` |
| 6 | Routers import `redis` / hardcode client → cannot swap backends | `RateLimiterBackend` + `CacheBackend` Protocols; factory from `REDIS_URL`; redis only in backend modules |
| 7 | Cache key omits base lat/lng → wrong hit across different start points | Key includes `round(base_lat,3)` + `round(base_lng,3)` (blueprint) |
| 8 | Second graph invoke path in router → dual ToolContext / timeout logic | **Only** `PlannerService.generate(...)` runs the graph |
| 9 | Soft-delete / list without ownership → IDOR | List `require_auth`; get/delete ownership guards; GeoJSON public by UUID only |
| 10 | P7 edit endpoints land in P6 | Forward-lock only — reorder/remove/add/reoptimize = **P7** |
| 11 | Redis outage → 500 on generate | Rate limit fail-open; cache skip → run agent fresh |
| 12 | Auto-save never for guests → no `trip_id` in SSE | Auto-save guests with `user_id=None` + `session_id` when plan usable |

---

## Prerequisites (P5 must be complete)

**Gate — do NOT implement P6 code until all of the following are true:**

- `docs/context.md` shows P5.1–5.14 ✅ (or equivalent ship) and Next step → P6.1
- `PlannerService.generate` real in `src/planner/service.py` (`wait_for`, `on_event`, fresh `ToolContext`)
- `get_compiled_graph()` compiles; `python scripts/test_agent.py` green (or documented env blocker)
- `python -m pytest tests/ -v` green for P5 suite
- Trip / TripPlace / TripEditEvent **models** exist (P1); trips repo/service/router/schemas are still stubs (~1 line)
- `RateLimiterBackend` + `InMemoryRateLimiter` + path table already exist (P1/P2); Redis backend **not** wired yet
- `REDIS_URL` in settings (may be `""`); `PLANNER_ABSOLUTE_MIN_PLACES` **not** in settings yet — add in 6.2
- Cookie name **`wandr_session`** already used in `src/auth/router.py` (`COOKIE_SESSION`)

**Already real (do NOT reinvent):**

- `src/planner/service.py` — `PlannerService.generate(..., on_event=...)`
- `src/planner/graph/*` — compiled phase-gated agent
- `src/core/middleware/rate_limit.py` — Protocol + in-memory + fail-open
- `src/core/llm/client.py` — only litellm import; swap model via `LLM_MODEL`
- `src/planner/routing_provider.py` — `OsrmRoutingProvider` / `RoutingProvider`
- `src/trips/models.py` — Trip, TripPlace, TripEditEvent
- Destinations: `lat`, `lng`, `place_count` on model/service

**Current stubs (do NOT assume APIs):**

- `src/trips/{repository,service,router,schemas,exceptions}.py`
- `src/planner/{router,schemas}.py` (service is real; HTTP is not)
- Redis rate limiter / any `CacheBackend`

---

## Prompt conventions (every step)

- **Extend, don't replace** P0–P5 code unless the step explicitly says replace.
- **Layering:** Router → Service → Repository only. Routers never touch DB or Redis clients.
- **LLM rule:** only via `src/core/llm/client.py`. Never import litellm/groq/openai elsewhere.
- **Geo rule:** only via `src/geo/` (routing still through `RoutingProvider` → `geo/osrm`).
- **Travel engine purity:** unchanged — no I/O in `travel_engine/`.
- **Env:** all via `get_settings()` — never `os.environ.get()`.
- **Envelopes:** `ApiResponse[T]` / `PaginatedResponse[T]` / `ErrorResponse` — never raw dict responses for JSON APIs. SSE frames are event-stream (not ApiResponse).
- **Time:** `datetime.now(timezone.utc)` for timestamps; schedule times remain naive `"HH:MM"`.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **No new packages** without `requirements.txt` + why-comment. Expected optional package in P6: `redis` (async) at 6.4.
- **Failure standards:** every code prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line.
- **OpenSpec cadence (implementation):** batch clusters — `6.1`, `6.2`, `6.3`, `6.4–6.5`. Do **not** run full propose→apply→archive for every single micro-step.

---

## P6 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         P6 dependency graph (canonical order)                │
└──────────────────────────────────────────────────────────────────────────────┘

  6.1 trips repository + TripService.save_from_state + ownership + schemas
        │
  6.2 planner/schemas + POST /planner/generate SSE (floor → Queue → generate)
        │
  6.3 trips/router CRUD + GeoJSON
        │
  6.4 Redis RateLimiterBackend + CacheBackend planner cache
        │
  6.5 ship checklist + pytest/smoke + context.md

  Abstraction / DI map (swap providers without rewriting routers):

    FastAPI Router
      │
      ├─► PlannerService.generate(on_event=...)     # HTTP-agnostic (P5)
      │     └─► graph + ToolContext.routing: RoutingProvider
      │
      ├─► TripService → TripRepository              # UoW save / ownership
      │
      └─► CacheBackend (Protocol)                   # InMemory | Redis
            get_cache_backend() ← REDIS_URL

    RateLimitMiddleware
      └─► RateLimiterBackend (Protocol)            # InMemory | Redis
            get_rate_limiter() ← REDIS_URL

    LLM (unchanged)  → core/llm/client.py ← LLM_MODEL env
    Geo (unchanged)  → src/geo/* gateways
```

**Canonical build order (the only order stated in this document):**
```
6.1 → 6.2 → 6.3 → 6.4 → 6.5
```

**SSE shape (LOCKED):**
```
Client ──POST /api/v1/planner/generate──► Router
  1) optional_auth + ensure wandr_session
  2) load destination; if place_count < PLANNER_ABSOLUTE_MIN_PLACES → 409
  3) default base_lat/lng ← destination.lat/lng when omitted
  4) (6.4+) cache lookup → short SSE itinerary_done if hit
  5) queue = asyncio.Queue(); on_event = enqueue
  6) task = asyncio.create_task(PlannerService.generate(..., on_event=on_event))
  7) async for: poll queue → yield SSE; if disconnected → task.cancel()
  8) on usable plan_complete → TripService.save_from_state; include trip_id in itinerary_done
```

---

## P6 design decisions (locked — no "optional" / either-or)

### Abstraction & provider swap — LOCKED

| Concern | Protocol / gateway | Dev (`REDIS_URL=""`) | Prod (`REDIS_URL` set) | Swap mechanism |
|---------|-------------------|----------------------|------------------------|----------------|
| Rate limit | `RateLimiterBackend` | `InMemoryRateLimiter` | `RedisRateLimiter` | `get_rate_limiter()` |
| Planner cache | `CacheBackend` | `InMemoryCacheBackend` | `RedisCacheBackend` | `get_cache_backend()` |
| Routing | `RoutingProvider` | Fake in tests / OSRM | OSRM | ToolContext DI |
| LLM | `chat_*` in `core/llm` | any litellm model | same | `LLM_MODEL` env only |

Routers and domain services MUST NOT `import redis`. Only backend modules under `src/core/` may.

### Guest ownership — LOCKED

- Cookie: `wandr_session` (same as auth router).
- Unauthenticated get/delete (where allowed): cookie value MUST equal `Trip.session_id`.
- Mismatch or missing → **HTTP 403** + `ErrorResponse` (never 404 for ownership miss).
- Authenticated: `Trip.user_id` must match current user (or claim rule if session matches — implement ownership helper once; reuse in 6.2/6.3).

### Absolute min-places floor — LOCKED

- Settings: `PLANNER_ABSOLUTE_MIN_PLACES: int = 10`
- Check **before** `generate` / cache miss path that would run the agent
- HTTP **409 Conflict**, code `destination_not_ready`
- Soft readiness (`PLANNER_MIN_READINESS_SCORE`) remains in-graph warning only — do not conflate

### SSE events — LOCKED (names)

```
preferences_done | phase_changed | tool_started | tool_done
validation_done | itinerary_done | clarification_needed | error
```

Framing: standard SSE (`event: …` / `data: …\n\n`). Map service `on_event(event, data)` names onto this set (normalize aliases in router if needed).

### Trip save — LOCKED

- `save_from_state(state, user_id, session_id) → Trip` in **one** DB transaction
- Auto-save when generation yields usable itinerary (`plan_complete` / non-empty schedule) — guests get `user_id=None`
- Do **not** create Trip rows for empty abort / clarification-only with no itinerary
- Evaluation always (P5 service) — independent of Trip save

### Planner cache — LOCKED

```
key = sha256(
  f"{destination_id}:{','.join(sorted(interests))}:{days}:{budget}:"
  f"{round(base_lat, 3)}:{round(base_lng, 3)}"
)
TTL = PLANNER_CACHE_TTL_SECONDS (default 3600)
```

- Cache-aside at **parsed-preference** level (MVP: free-text nuance beyond parse may be dropped on hit)
- Hit → SSE short path to `itinerary_done` **without** tool loop; still subject to rate limit
- Backend error / miss → run agent fresh; never 500

### Auth matrix — LOCKED

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/planner/generate` | `optional_auth` |
| GET | `/api/v1/trips` | `require_auth` |
| GET | `/api/v1/trips/{id}` | `optional_auth` + ownership |
| GET | `/api/v1/trips/{id}/geojson` | public |
| DELETE | `/api/v1/trips/{id}` | `require_auth` + ownership |

### Design patterns (teaching + structure)

| Module | Pattern | Meaning |
|--------|---------|---------|
| `TripService.save_from_state` | Unit of Work | Trip + places one transaction |
| `RateLimiterBackend` / `CacheBackend` | Strategy + Protocol | In-memory ↔ Redis via settings |
| Planner router + Queue | Ports & Adapters | SSE adapter over HTTP-agnostic service |
| `OsrmRoutingProvider` | Adapter (P4) | Injected routing |
| `core/llm/client.py` | Gateway | Model swap via env |
| Ownership helper | Policy / Guard | Guest session ≡ user ownership |

### Forward locks (design-only — do not implement in P6)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Edit/replan HTTP API (reorder/remove/add/reoptimize) | P7 |
| F2 | `record_edit` + `user_edited` on evaluation | P7 |
| F3 | Daily LLM spend caps | post-MVP |
| F4 | Redis in docker-compose / multi-region | not required for MVP |

---

## Step 6.1 — trips/ repository + service (save_from_state + ownership)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement TripRepository + TripService persistence + schemas/exceptions.
This is step 6.1. No FastAPI planner generate yet. No Redis. No new packages.

─── IMPLEMENT / EXTEND ───

  src/trips/exceptions.py
    - TripNotFoundError, TripForbiddenError (map to 404 / 403 via existing exception handlers if present;
      else raise WandrError subclasses consistent with auth/destinations)

  src/trips/schemas.py
    - TripOut, TripPlaceOut (Pydantic) — include days, status, preferences, stops with
      suggested_start_time, visit_duration_min, lat/lng when joined, polyline optional
    - Keep fields aligned with Trip / TripPlace models — no invent columns / no migration

  src/trips/repository.py
    - class TripRepository(BaseRepository[Trip, UUID])
    - list_by_user(user_id, *, page params) / list_by_session(session_id, ...)
    - get_with_places(trip_id) — eager load TripPlace (+ Place coords if needed for GeoJSON later)
    - Soft-delete aware via BaseRepository; TripPlace has no SoftDeleteMixin

  src/trips/service.py
    - save_from_state(state, user_id: UUID | None, session_id: str) → Trip
        Map schedule/route/itinerary → Trip + TripPlace rows
        Single transaction: create trip, insert all places, commit
        status COMPLETE when plan usable; preferences JSONB from state prefs
        On any failure → rollback; never leave Trip without places
    - assert_can_access(trip, *, user_id, session_id, require_user: bool) → None
        Guest: session_id must equal trip.session_id else TripForbiddenError
        User: trip.user_id == user_id (if require_user / authenticated path)
    - Optional thin claim_for_user(trip, user_id) when session matches — only if tests need it;
      no dedicated HTTP claim route in P6

─── RULES ───
- Router not required in 6.1 (can leave stub); service must be unit-testable with db_session.
- Do not call PlannerService from trips service.
- Flush/commit patterns: match existing domain services (auth upsert commits; BaseRepository flush-only —
  service owns commit boundary for UoW).

─── FAILURE BOUNDARY ───
Partial TripPlace insert → full rollback. Must NOT: commit orphan Trip.
Ownership miss → TripForbiddenError (403). Must NOT: 404 for wrong session.

─── VALIDATION ───
  python -c "
from src.trips.repository import TripRepository
from src.trips.service import TripService
assert hasattr(TripService, 'save_from_state')
print('PASS — 6.1 trips service/repo surface')
"

  # Prefer tests/trips/test_save_from_state.py (land with 6.5 if needed):
  # save → get_with_places all stops; forced mid-insert fail → no Trip row

✅ Failure path: simulated place insert failure → zero committed trips for that attempt.
```

---

## Step 6.2 — planner/router.py — POST /generate streaming SSE

```
Read AGENT.md and docs/context.md before proceeding.

TASK: HTTP SSE adapter over PlannerService.generate. This is step 6.2.
Add PLANNER_ABSOLUTE_MIN_PLACES to settings. Register planner router in main.py.

─── UPDATE src/config.py ───

  PLANNER_ABSOLUTE_MIN_PLACES: int = 10
  # optional now or at 6.4: PLANNER_CACHE_TTL_SECONDS: int = 3600

─── IMPLEMENT src/planner/schemas.py ───

  PlanRequest:
    destination_id: UUID
    raw_input: str
    days: int | None = None          # optional hint; parse_preferences still runs
    base_lat: float | None = None
    base_lng: float | None = None

─── IMPLEMENT src/planner/router.py ───

  POST /api/v1/planner/generate
    - Depends(optional_auth); ensure wandr_session cookie (reuse auth helper pattern /
      duplicate thin ensure like auth router — do not break auth module)
    - Resolve destination via DestinationService/Repository (404 if missing)
    - If destination.place_count < PLANNER_ABSOLUTE_MIN_PLACES → 409 ErrorResponse
      code=destination_not_ready — return BEFORE StreamingResponse / generate
    - Default base_lat/lng to destination.lat/lng when omitted
    - StreamingResponse media_type="text/event-stream"
    - LOCKED runtime shape:
        queue: asyncio.Queue
        def on_event(event, data): queue.put_nowait((event, data))  # or async-safe variant
        task = asyncio.create_task(
          PlannerService().generate(
            destination_id=..., raw_input=..., base_lat=..., base_lng=...,
            session_id=..., on_event=on_event,
          )
        )
        async def event_gen():
          try:
            while not task.done() or not queue.empty():
              if await request.is_disconnected():
                task.cancel(); break
              # wait briefly for queue item or task completion
              ...
              yield sse_frame(event, data)
            # drain remaining; if final state usable → save_from_state; emit itinerary_done with trip_id
          finally:
            if not task.done():
              task.cancel()
    - Must NOT: final = await generate(...); then for e in buffer: yield e
    - Must NOT: import StreamingResponse inside planner/service.py
    - On timeout: service already emits error via on_event — stream closes cleanly
    - clarification_needed / error paths: no trip save (unless usable partial — LOCKED: save only usable plan_complete itinerary)

─── REGISTER ───

  main.py include_router(planner.router, prefix consistent with /api/v1)

─── RULES ───
- Cache wiring is 6.4 — 6.2 may stub a no-op miss path.
- Auto-save via TripService from 6.1.
- Rate limit path already configured for /api/v1/planner/generate (10/min) — do not hardcode a second limiter in router.

─── FAILURE BOUNDARY ───
place_count below floor → 409, no graph. Disconnect → cancel task. Timeout → SSE error + close.
Must NOT: hang; Must NOT: await-full-invoke-then-dump.

─── VALIDATION ───
  python -c "
from src.main import create_app
app = create_app()
paths = [getattr(r,'path',None) for r in app.routes]
assert any(p and 'planner/generate' in p for p in paths)
print('PASS — 6.2 generate route registered')
"

  Get-ChildItem -Path src\planner\service.py | Select-String "StreamingResponse|is_disconnected"
  # Expected: zero matches

  # Manual / testclient: curl -N POST generate → events while running
  # Monkeypatch generate sleep > timeout → error event then close

✅ Failure path: destination with place_count=0 → 409 destination_not_ready (assert in tests).
```

---

## Step 6.3 — trips/router.py — CRUD + GeoJSON

```
Read AGENT.md and docs/context.md before proceeding.

TASK: HTTP trips API + GeoJSON builder. This is step 6.3. Register trips router.

─── IMPLEMENT TripService.build_geojson (or trips/geojson.py helper) ───

  - Input: trip with places/polylines/coords already loaded
  - Output: GeoJSON FeatureCollection (LineString / Point features as appropriate)
  - NO live OSRM / httpx — pure from DB fields

─── IMPLEMENT src/trips/router.py ───

  GET    /api/v1/trips              → PaginatedResponse[TripOut]  (require_auth)
  GET    /api/v1/trips/{id}         → ApiResponse[TripOut]        (optional_auth + ownership)
  GET    /api/v1/trips/{id}/geojson → GeoJSON FeatureCollection   (public — no ownership)
  DELETE /api/v1/trips/{id}         → 204                          (require_auth + ownership)

  Ownership via TripService.assert_can_access — 403 on miss.

─── RULES ───
- Soft-delete on DELETE (Trip has SoftDeleteMixin) unless project convention is hard delete —
  prefer BaseRepository soft-delete.
- Do not add P7 edit routes.

─── FAILURE BOUNDARY ───
Wrong owner / guest session mismatch → 403. Missing trip → 404.
Must NOT: 500 on ownership miss; Must NOT: call OSRM in geojson.

─── VALIDATION ───
  python -c "
from src.main import create_app
app = create_app()
paths = [getattr(r,'path',None) for r in app.routes]
assert any(p and p.rstrip('/').endswith('/trips') or (p and '/trips/' in p) for p in paths)
print('PASS — 6.3 trips routes present', [p for p in paths if p and 'trips' in p])
"

  # Testclient: save trip → GET geojson → json load FeatureCollection
  # Guest wrong wandr_session → 403 on GET /trips/{id}

✅ Failure path: other user's trip → 403.
```

---

## Step 6.4 — Redis rate limiter + planner CacheBackend

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Swappable Redis backends behind Protocols + planner cache-aside on generate.
This is step 6.4.

─── PACKAGES ───

  If needed: redis[hiredis] or redis>=5 async — append requirements.txt with why-comment
  # P6.4 — optional REDIS_URL backends for rate limit + planner cache

─── IMPLEMENT CacheBackend ───

  Prefer src/core/cache/backends.py (or adjacent module):

    class CacheBackend(Protocol):
        async def get(self, key: str) -> str | None: ...
        async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    InMemoryCacheBackend
    RedisCacheBackend  # only constructed when REDIS_URL set

  def get_cache_backend() -> CacheBackend:
      settings = get_settings()
      if settings.REDIS_URL:
          return RedisCacheBackend(...)
      return InMemoryCacheBackend()

  Explicit connect/read timeouts on Redis client. Errors on get/set → log + treat as miss / no-op set.

─── EXTEND rate_limit.py ───

  RedisRateLimiter(RateLimiterBackend) when REDIS_URL set
  get_rate_limiter() selects InMemory vs Redis
  Fail-open unchanged

─── WIRE planner cache into generate path (router or thin PlannerService helper) ───

  - Build cache key per locked formula (include rounded base coords)
  - On hit: stream short SSE ending itinerary_done from cached JSON — skip tool loop
  - On miss: run generate; if success, set cache best-effort
  - Settings: PLANNER_CACHE_TTL_SECONDS = 3600

─── RULES ───
- No redis imports in src/planner/router.py or src/trips/* — only via get_cache_backend / get_rate_limiter
- Empty REDIS_URL → pure in-memory (docker-compose stays without Redis)
- LLM_MODEL / RoutingProvider unchanged

─── FAILURE BOUNDARY ───
Redis down → fail-open rate limit; skip cache; generation continues. Must NOT: 500.

─── VALIDATION ───
  python -c "
from src.core.middleware.rate_limit import get_rate_limiter, InMemoryRateLimiter
from src.config import get_settings
# With default empty REDIS_URL:
assert isinstance(get_rate_limiter(), InMemoryRateLimiter) or type(get_rate_limiter()).__name__
print('PASS — 6.4 limiter factory import', type(get_rate_limiter()).__name__)
"

  Get-ChildItem -Path src\planner,src\trips -Recurse -Filter *.py |
    Select-String "import redis|from redis"
  # Expected: zero matches

  # Same PlanRequest twice (same prefs/base) → second path hits cache (unit/integration)
  # 11th rapid generate → 429 Retry-After

✅ Failure path: mock Redis raising → generate still succeeds (skip cache / fail-open).
```

---

## Step 6.5 — Backend ship checklist + pytest/smoke + context.md

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close P6 with tests, smoke, import guards, and context update. This is step 6.5.
Update docs/context.md ONLY after validations pass.

─── TESTS (create/extend) ───

  tests/trips/ — save_from_state UoW, ownership 403, geojson shape, list auth
  tests/planner/ — generate 409 floor, SSE event order smoke with mocked generate,
                   disconnect cancel (if feasible), cache hit skips graph (spy)
  tests/core/ — Redis limiter selection + fail-open (mocked)

─── SMOKE / MANUAL PROOF ───

  scripts/test_p6_smoke.py (optional but preferred) OR document curl sections:
    1) destinations/search Darjeeling
    2) readiness
    3) places page
    4) curl -N POST /api/v1/planner/generate → tool_started/tool_done → itinerary_done
    5) GET trip geojson
    6) second identical generate → fast cache path (if 6.4 live)
    7) import guards

─── UPDATE docs/context.md (ONLY after green) ───

  - Last updated / Next step → P7.1
  - Progress 6.1–6.5 ✅
  - Implemented modules: trips repo/service/router, planner HTTP SSE, cache backends
  - Live endpoints: POST /planner/generate, trips CRUD + geojson
  - Stubs: remove trips/planner HTTP stubs; keep P7 edit ops as stubs/unimplemented
  - Do NOT claim P7 complete

─── FAILURE BOUNDARY ───
Any checklist miss → do not mark P6 done in context.md.
Must NOT: print ALL PASSED if a section failed.

─── VALIDATION ───
  python -m pytest tests/ -v
  # plus smoke script / curl checklist below

✅ Failure path: failing pytest blocks context.md P6 complete update.
```

---

## P6 Complete — Full Verification Checklist

Before claiming P6 done in `docs/context.md`:

```bash
# ── Unit / integration ──
python -m pytest tests/ -v

# ── Routes registered ──
python -c "from src.main import create_app; app=create_app(); paths=[getattr(r,'path',None) for r in app.routes]; assert any(p and 'planner/generate' in p for p in paths); assert any(p and 'trips' in p for p in paths); print('routes ok')"

# ── Import guards (PowerShell) ──
Get-ChildItem -Path src -Recurse -Filter *.py |
  Select-String "import litellm|from litellm" |
  Where-Object { $_.Path -notmatch "core\\llm\\client\.py" }
# Expected: zero matches

Get-ChildItem -Path src\travel_engine -Recurse -Filter *.py |
  Select-String "src\.geo|import httpx|litellm|qdrant"
# Expected: zero matches

Get-ChildItem -Path src\planner\graph\nodes -Recurse -Filter *.py |
  Select-String "from src\.planner\.tools\.(check_readiness|search_places|rank_places|build_route)"
# Expected: zero matches

Get-ChildItem -Path src\planner\router.py,src\trips -Recurse -Filter *.py |
  Select-String "import redis|from redis"
# Expected: zero matches

Get-ChildItem -Path src\planner\service.py |
  Select-String "StreamingResponse|is_disconnected"
# Expected: zero matches

# ── Blueprint P6.5 checklist (manual / smoke) ──
# [ ] ErrorResponse / PaginatedResponse envelopes on JSON APIs
# [ ] GET destinations/search?q=Darjeeling
# [ ] GET destinations/{id}/readiness
# [ ] GET places?destination_id=...&page=2
# [ ] POST planner/generate → SSE tool events + itinerary_done
# [ ] GET trips/{id}/geojson → valid GeoJSON
# [ ] Stops include suggested_start_time + visit_duration_min
# [ ] Happy-path resilience flags sane; evaluation rows written
# [ ] Max tools / REPLAN ceilings still honored (P5)
# [ ] finish_plan / phase gating still tested
# [ ] docker compose up from clean state works (no Redis required)
# [ ] No hardcoded secrets/URLs — get_settings()
# [ ] Kill LLM during loop → fallback / clean error event
# [ ] Change LLM_MODEL → zero code changes
# [ ] 11th rapid generate → 429
# [ ] Same cacheable input twice → 2nd fast (cache)

echo "P6 COMPLETE — proceed to P7"
```

### P6 ship criteria

| Check | Expected |
|-------|----------|
| Trip UoW | Save + get_with_places; rollback on partial fail |
| Guest ownership | Session mismatch → 403 |
| SSE generate | Streaming while running; timeout/disconnect safe |
| Absolute min places | 409 before graph |
| Service purity | No StreamingResponse in planner/service.py |
| Trips CRUD + GeoJSON | Auth matrix; public geojson; no live OSRM on read |
| Protocol backends | REDIS_URL selects Redis; empty → in-memory |
| Fallbacks | Redis down → fail-open + skip-cache |
| Provider swap | LLM_MODEL / RoutingProvider / cache-rate factories |
| Import guards | litellm / travel_engine / redis / tool-impl |
| pytest + smoke | Green; context.md updated only after |
| P7 edits | **Not** registered |

### Recommended OpenSpec implementation batches

After this prompt is archived / ready, implement with batched changes:

1. `6.1` — trips repository + `save_from_state` + ownership + schemas  
2. `6.2` — planner schemas + SSE generate router + absolute min-places + main registration  
3. `6.3` — trips CRUD + GeoJSON  
4. `6.4–6.5` — Redis rate/cache + tests/smoke + `context.md`  

Do **not** open a full propose→archive cycle for each micro-detail inside a step unless a design conflict appears.
