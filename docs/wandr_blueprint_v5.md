# Wandr — Backend Blueprint v5
> Production-grade AI travel planner (map visualization lives in a separate frontend blueprint). Modular monolith. Thin vertical slices. Every step ends with a runnable proof.

**Supersedes:** `wandr_blueprint_v4.md` (v4 remains unchanged as historical reference)

---

## What's new in v5

| Area | v4 | v5 |
|------|----|----|
| Agent model | Linear LangGraph pipeline | **Controlled hybrid agent** — deterministic pipeline + typed tools + bounded replan loop |
| Iteration guard | Per-node counter (bug: aborts before itinerary) | **`replan_loop_count`** — only increments on validation-driven replans |
| `travel_engine` I/O | Contradiction: "no I/O" but calls OSRM | **Pure Python** — routing injected via `RoutingProvider` protocol; nodes/tools call `geo/` |
| Accommodation | Implicit "center" | **`base_lat` / `base_lng`** on `PlanRequest`; defaults to destination center |
| Itinerary output | Order + travel time only | **`suggested_start_time` + `visit_duration_min`** per stop via `schedule_builder` |
| Destination quality | Not tracked | **`readiness` score** — place count, enrichment %, index %; surfaced before generation |
| User edits | Eval signal only (`user_edited`) | **P7 Edit & Replan APIs** — reorder, add, remove, day re-optimize |
| Tool calls | None | **`planner/tools/`** — typed tool registry; replan supervisor picks from fixed action enum |
| Phases | P0–P6 (~25 days) | **P0–P7 (~30 days backend)** |

---

## Principles

| # | Principle |
|---|-----------|
| 1 | **Packages at point of use** — nothing installed until the step that needs it |
| 2 | **LLD pattern named per step** — every design decision is explicit |
| 3 | **Failure boundary per step** — every external call has a fallback |
| 4 | **Production layer abstracted from step 1** — same code runs locally and in prod via env vars |
| 5 | **Lightest viable package** — no heavy dependencies without justification |
| 6 | **Travel intelligence is a first-class layer** — not buried in LangGraph nodes |
| 7 | **Evaluation from day one** — every generated trip is stored for quality analysis |
| 8 | **LLM provider is swappable** — all LLM calls go through `core/llm/client.py` only |
| 9 | **Resilience is mandatory** — every external call has explicit timeouts, retry strategy, and a named fallback |
| 10 | **Controlled AI-assisted dev** — `AGENT.md` guardrails prevent uncontrolled Cursor output |
| 11 | **Structure from code, narrative from LLM** — itinerary geometry, order, and times never come from free-form LLM output |
| 12 | **Tools are typed contracts** — all planner tools have Pydantic input/output schemas; no ad-hoc dict plumbing |

---

## AGENT.md — AI Coding Guardrails
> **Create this file at repo root before opening Cursor. Reference it at the start of every session prompt.**

```markdown
# AGENT.md — Wandr Coding Guardrails

## Hard rules — never violate, never simplify away

### Architecture
- Router calls Service only. Service calls Repository only. Router never touches DB directly.
- LLM calls happen ONLY through `src/core/llm/client.py`. Never import litellm, groq, or openai directly anywhere else.
- Geo calls happen ONLY through `src/geo/`. Never call Nominatim, Overpass, or OSRM directly outside this module.
- Planner side effects (search, routing, DB) happen ONLY through `src/planner/tools/` or domain services — never inline in nodes.
- `travel_engine/` has NO LLM calls and NO network/DB I/O. Pure Python only. Routing times are passed in or returned via injected `RoutingProvider` from caller.
- `evaluation/` records every generation and every edit. Never skip this, even on partial failures.

### Resilience (non-negotiable)
- Every httpx call MUST have explicit connect_timeout and read_timeout set.
- Every external call MUST use tenacity retry. See Resilience Contracts table in blueprint.
- Every external call MUST have a named fallback. Never let an external failure raise a 500.
- LangGraph replan loop MUST check `replan_loop_count < max_replan_attempts` before entering replan path.
- The SSE stream MUST be wrapped in asyncio.wait_for with PLANNER_GENERATION_TIMEOUT_SECONDS ceiling (default 45s).

### Agent / tools (non-negotiable)
- Replan supervisor LLM output MUST be JSON matching `ReplanAction` enum — never free-text tool selection.
- Tool implementations live in `planner/tools/*.py` and are registered in `planner/tools/registry.py`.
- Nodes call tools via `execute_tool(name, input)` — never call tool impl functions directly from nodes.
- LLM never outputs place IDs, coordinates, or stop order. Those come from travel_engine + tools only.

### Code conventions
- All env var access through `get_settings()`. Never `os.environ.get()` directly.
- Every new endpoint returns `ApiResponse[T]` or `PaginatedResponse[T]`. Never a raw dict.
- No new packages without appending to requirements.txt with a comment explaining why.
- No hardcoded strings, numbers, or URLs. All constants in `travel_rules.py` or `config.py`.

### When in doubt
- Check the Resilience Contracts table before adding any external call.
- If a node needs to call an LLM, go through `core/llm/client.py` — no exceptions.
- If unsure about a timeout value, use the value from the Resilience Contracts table.
```

---

## Project Structure

```
wandr-backend/
├── AGENT.md
├── alembic/
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── scripts/
│   ├── seed_destination.py
│   ├── enrich_places.py
│   ├── index_places.py
│   ├── test_travel_engine.py
│   └── test_agent.py
├── tests/
│   ├── conftest.py
│   ├── auth/
│   ├── planner/
│   ├── geo/
│   ├── trips/
│   └── destinations/
└── src/
    ├── main.py
    ├── config.py
    │
    ├── core/
    │   ├── llm/
    │   │   └── client.py           # LiteLLM wrapper — ONLY LLM entry point
    │   ├── database/
    │   │   ├── base.py
    │   │   ├── session.py
    │   │   └── base_repository.py
    │   ├── security/
    │   │   ├── jwt.py
    │   │   └── permissions.py
    │   ├── middleware/
    │   │   ├── logging.py
    │   │   └── rate_limit.py
    │   ├── observability/
    │   │   ├── logging.py
    │   │   └── tracing.py
    │   ├── pagination.py
    │   ├── responses.py
    │   └── exceptions.py
    │
    ├── auth/
    ├── destinations/
    │   ├── router.py               # + GET /{id}/readiness
    │   ├── schemas.py              # + DestinationReadinessOut
    │   ├── models.py
    │   ├── repository.py
    │   ├── service.py              # + compute_readiness()
    │   └── readiness.py            # ★ pure scoring logic
    │
    ├── places/
    ├── trips/
    │   ├── router.py               # + edit/replan endpoints (P7)
    │   ├── schemas.py              # + ReorderStopsIn, AddStopIn, TripEditOut
    │   ├── models.py               # + TripEditEvent
    │   ├── repository.py
    │   ├── service.py              # + reorder, remove, add, reoptimize_day
    │   └── exceptions.py
    │
    ├── planner/
    │   ├── router.py               # POST /generate (SSE), POST /clarify (optional)
    │   ├── schemas.py              # PlanRequest (+ base_lat/lng), PlanResult, ItineraryDay, ItineraryStop
    │   ├── service.py
    │   ├── routing_provider.py     # ★ OsrmRoutingProvider implements RoutingProvider for tools
    │   ├── tools/                  # ★ typed tool layer — nodes call execute_tool() only
    │   │   ├── registry.py         # TOOL_REGISTRY + execute_tool()
    │   │   ├── schemas.py          # Tool I/O Pydantic models, ReplanAction enum
    │   │   ├── check_readiness.py
    │   │   ├── search_places.py
    │   │   ├── rank_places.py
    │   │   ├── build_route.py
    │   │   ├── build_schedule.py
    │   │   └── validate_itinerary.py
    │   └── graph/
    │       ├── state.py
    │       ├── builder.py          # hybrid graph with conditional replan edges
    │       └── nodes/
    │           ├── readiness_check.py
    │           ├── preference.py
    │           ├── clarification.py  # optional — emits needs_input, does not block MVP path
    │           ├── poi_retrieval.py
    │           ├── ranking.py
    │           ├── route_planner.py
    │           ├── schedule_builder.py
    │           ├── itinerary.py
    │           ├── validation.py
    │           └── replan_supervisor.py  # ★ LLM picks ReplanAction from fixed enum
    │
    ├── travel_engine/              # ★ pure Python — no LLM, no network, no DB
    │   ├── travel_rules.py
    │   ├── protocols.py            # RoutingProvider, TravelTimeMatrix protocols
    │   ├── place_selector.py
    │   ├── day_allocator.py
    │   ├── route_optimizer.py      # accepts RoutingProvider — never imports geo/
    │   ├── schedule_builder.py     # ★ morning slots, visit durations → suggested_start_time
    │   └── trip_validator.py
    │
    ├── evaluation/
    │   ├── models.py               # TripEvaluation + TripEditEvent linkage
    │   ├── repository.py
    │   ├── service.py              # record_generation(), record_edit()
    │   └── schemas.py
    │
    ├── geo/
    └── search/
```

---

## Environment Variables

```bash
# Core
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=

# Database
DATABASE_URL=

# Vector search
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Cache
REDIS_URL=

# LLM — provider-agnostic via LiteLLM
LLM_MODEL=nvidia_nim/meta/llama-3.1-8b-instruct
LLM_API_KEY=
LLM_API_BASE=
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=4

# Planner agent bounds
PLANNER_MAX_REPLAN_ATTEMPTS=2          # replan_loop_count ceiling — NOT per-node
PLANNER_GENERATION_TIMEOUT_SECONDS=45  # SSE asyncio.wait_for ceiling
PLANNER_MIN_READINESS_SCORE=0.3        # below this → warning in SSE, generation still allowed

# Observability
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Geo
NOMINATIM_USER_AGENT=wandr-dev-yourname@email.com
OSRM_BASE_URL=https://router.project-osrm.org
```

---

## Resilience Contracts
> Non-negotiable. Reference when implementing any external call.

| Component | Retry Strategy | Timeouts | 429 Handling | Final Fallback |
|---|---|---|---|---|
| `geo/geocoder.py` | tenacity 3x, exponential 1–8s | connect=5s, read=10s, total=15s | N/A | return `None` → `DestinationNotFound` |
| `geo/overpass.py` | tenacity 3x, exponential 2–16s | connect=10s, read=30s | N/A | return `[]` |
| `geo/osrm.py` | tenacity 2x, fixed 1s | connect=5s, read=10s | N/A | haversine × 1.4 |
| `core/llm/client.py` | tenacity 4x, exponential 2–30s | `LLM_TIMEOUT_SECONDS` | sleep `Retry-After`, retry | raise `WandrLLMError` |
| LangGraph (total) | no retry | `PLANNER_GENERATION_TIMEOUT_SECONDS` | N/A | SSE `error` event, close stream |
| LangGraph replan loop | bounded | N/A | N/A | `replan_loop_count >= max` → accept partial, route to validation |
| `planner/tools/*` | inherit callee contract | inherit | inherit | tool returns `ToolResult(ok=False, fallback_used=True)` — never raises to graph |
| `search/places_index.py` | no retry | N/A | N/A | return `[]` → PostGIS fallback |

**Retry only on:** `httpx.TimeoutException`, `httpx.ConnectError`, `litellm.Timeout`, `litellm.RateLimitError`  
**Never retry on:** 404, 422, 400, or any client error

---

## API Contracts (backend — map frontend consumes these separately)

### PlanRequest
```python
class PlanRequest(BaseModel):
    destination_id: UUID
    raw_input: str
    days: int | None = None              # optional override; preference node may parse from raw_input
    base_lat: float | None = None        # accommodation / start point; defaults to destination center
    base_lng: float | None = None
    accommodation_label: str | None = None  # display only, e.g. "Hotel on Mall Road"
```

### ItineraryStop (controlled output shape)
```python
class ItineraryStop(BaseModel):
    place_id: UUID
    name: str
    lat: float
    lng: float
    order: int                           # 1-based within day
    category: str
    travel_time_min: int                 # from previous stop (0 for first stop of day)
    visit_duration_min: int              # from VISIT_DURATION_BY_CATEGORY
    suggested_start_time: str            # "HH:MM" 24h — from schedule_builder, NOT from LLM
    arrival_note: str | None = None      # e.g. "Start early — 45min drive"
```

### ItineraryDay
```python
class ItineraryDay(BaseModel):
    day: int
    title: str                           # LLM narrative
    narrative: str                       # LLM narrative
    total_distance_km: float
    total_travel_min: int
    polyline: str                        # encoded, from geo/osrm via tools
    places: list[ItineraryStop]          # order + times from travel_engine only
```

### SSE event sequence (POST /api/v1/planner/generate)
```
event: readiness_done     data: {"score":0.82,"place_count":144,"warning":null}
event: preferences_done   data: {"days":3,"interests":["photography","offbeat"],...}
event: pois_found         data: {"count":36,"used_geo_fallback":false}
event: route_ready        data: {"days":3,"stops_per_day":[6,6,6]}
event: schedule_ready     data: {"days":3}   # times assigned
event: itinerary_done     data: {full ItineraryDay[] JSON}
event: replan_started       data: {"attempt":1,"action":"drop_weakest_stop"}   # only if replanning
event: error                data: {"code":"generation_timeout","message":"..."}
```

---

## travel_engine — Design
> Pure Python. No LLM. No network. No database. Callers inject routing data.

### protocols.py
```python
class RouteLeg(BaseModel):
    from_place_id: UUID
    to_place_id: UUID
    duration_min: int
    distance_km: float
    used_fallback: bool = False

class RoutingProvider(Protocol):
    async def travel_matrix(self, waypoints: list[tuple[UUID, float, float]]) -> list[RouteLeg]: ...
```

`OsrmRoutingProvider` lives in `planner/routing_provider.py` — wraps `geo/osrm.py`, implements protocol, sets `used_osrm_fallback` on state when haversine used.

### schedule_builder.py (new)
Answers: *what time should each stop start?*
- Input: ordered stops per day + `RouteLeg` travel times + `VISIT_DURATION_BY_CATEGORY`
- Constants from `travel_rules.py`: `DAY_START_TIME="08:00"`, `LUNCH_BREAK_START="13:00"`, `LUNCH_BREAK_MIN=60`
- Morning-only categories forced into first two slots with `suggested_start_time <= "10:30"`
- Output: same stops enriched with `visit_duration_min`, `suggested_start_time`, `arrival_note`
- Pure function — no LLM

### route_optimizer.py (updated)
- Signature: `optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider) → list[OrderedStop]`
- Calls `routing.travel_matrix()` — never imports `geo/`
- Drop-retry loop capped at 3 attempts (unchanged from v4)

---

## planner/tools — Design
> Typed tool layer. Nodes and replan supervisor invoke tools through `execute_tool()` only.

### registry.py
```python
TOOL_REGISTRY: dict[str, Callable] = {
    "check_readiness": check_readiness_tool,
    "search_places": search_places_tool,
    "rank_places": rank_places_tool,
    "build_route": build_route_tool,
    "build_schedule": build_schedule_tool,
    "validate_itinerary": validate_itinerary_tool,
}

async def execute_tool(name: str, input: BaseModel, ctx: ToolContext) -> ToolResult:
    # logs tool name, duration, fallback_used; never raises — returns ToolResult(ok=False) on failure
```

### ToolContext (passed into every tool)
```python
class ToolContext(BaseModel):
    destination_id: UUID
    base_lat: float
    base_lng: float
    routing: RoutingProvider
    db: AsyncSession
    state: TravelState          # read/write allowed fields only via typed helpers
```

### ReplanAction enum (replan supervisor — controlled tool call)
```python
class ReplanAction(str, Enum):
    REOPTIMIZE_ROUTES = "reoptimize_routes"       # re-run build_route for all days
    DROP_WEAKEST_STOP = "drop_weakest_stop"       # remove lowest-scored stop on worst day
    EXPAND_POI_SEARCH = "expand_poi_search"       # increase top_k by 50%, re-rank
    ACCEPT_PARTIAL = "accept_partial"               # exit replan loop with warnings
```

Replan supervisor node:
- Calls LLM with JSON schema `{ "action": ReplanAction, "reason": str }`
- On `WandrLLMError` → deterministic fallback: `DROP_WEAKEST_STOP` once, then `ACCEPT_PARTIAL`
- Increments `state.replan_loop_count` before executing chosen action
- Never allows free-form tool names from LLM

---

## destinations/readiness — Design

### readiness.py
```python
def compute_readiness(
    place_count: int,
    enriched_count: int,      # places with non-null summary
    indexed_count: int,       # places in Qdrant for destination (0 if search unavailable)
    search_available: bool,
) -> ReadinessResult:
    # score 0.0–1.0 weighted: place_count (0.4), enriched_pct (0.35), indexed_pct (0.25)
    # tier: "ready" >= 0.7, "limited" >= 0.3, "sparse" < 0.3
```

### GET /api/v1/destinations/{id}/readiness
Returns `ApiResponse[DestinationReadinessOut]`:
```python
class DestinationReadinessOut(BaseModel):
    destination_id: UUID
    score: float
    tier: Literal["ready", "limited", "sparse"]
    place_count: int
    enriched_pct: float
    indexed_pct: float
    message: str | None          # human-readable, e.g. "Limited POI data — results may be generic"
```

Planner `readiness_check` node calls `check_readiness` tool; if `score < PLANNER_MIN_READINESS_SCORE`, adds warning to state and SSE — **does not block generation**.

---

## Controlled Agent Graph — Design

```
START
  → readiness_check
  → preference
  → [clarification_needed?] → clarification → END (needs_input) OR continue
  → poi_retrieval
  → ranking
  → route_planner
  → schedule_builder
  → itinerary
  → validation
  → [validation.errors AND replan_loop_count < max?]
        → replan_supervisor → execute replan action → route_planner (loop)
     ELSE → END
```

**Key fix vs v4:** `replan_loop_count` increments only when entering replan path — not on every forward node. Happy path runs with `replan_loop_count=0`, `abort_triggered=False`.

### TravelState resilience fields (v5)
```python
replan_loop_count: int = 0
max_replan_attempts: int          # from settings.PLANNER_MAX_REPLAN_ATTEMPTS
abort_triggered: bool = False     # True when max replans exhausted
llm_retry_count: int = 0
used_geo_fallback: bool = False
used_osrm_fallback: bool = False
readiness_score: float | None = None
replan_actions_taken: list[str] = []
```

---

## evaluation — Design (v5 additions)

TripEvaluation adds:
```python
readiness_score: float | None
replan_loop_count: int
replan_actions_taken: list[str]
base_lat: float
base_lng: float
```

TripEditEvent (new model):
```python
class TripEditEvent:
    id: UUID
    trip_id: UUID
    edit_type: Literal["reorder", "remove_stop", "add_stop", "reoptimize_day"]
    day_number: int | None
    place_id: UUID | None
    payload: dict                   # before/after snapshot (stop order, etc.)
    created_at: datetime
```

`evaluation.service.record_edit()` called from trips service on every P7 mutation — powers `user_edited` quality signal.

---

## P7 — Edit & Replan API
> Backend support for interactive map edits (frontend blueprint is separate).

| Method | Path | Body | Behavior |
|--------|------|------|----------|
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` | Validate ownership; reorder `TripPlace.order_in_day`; re-run `build_schedule` + OSRM polyline for day; record edit |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | — | Remove stop; re-optimize remaining day via `build_route` tool; record edit |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | `{ "place_id": uuid }` | Insert at end; re-optimize day; validate day load; record edit |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | — | Re-run route + schedule for day only; update polylines; record edit |

All endpoints:
- `require_auth` + ownership check → 403 on mismatch
- Return `ApiResponse[TripOut]` with updated itinerary slice
- On validation failure after edit → 422 `ErrorResponse` with `details.validation_warnings` — trip unchanged (transaction rollback)
- 🚨 OSRM/LLM failure during reoptimize → apply same fallbacks as generation; never 500

---

## Phase Blueprint

> P0–P6 inherit v4 steps unless noted below. Steps marked **(v5)** are new or materially changed.

### P0 — Scaffold, Config & Core Conventions
**2 days · 10 steps** — same as v4 (0.1–0.10), plus:
- 0.1: include `planner/tools/`, `travel_engine/protocols.py`, `destinations/readiness.py` in skeleton
- 0.2: add `PLANNER_MAX_REPLAN_ATTEMPTS`, `PLANNER_GENERATION_TIMEOUT_SECONDS`, `PLANNER_MIN_READINESS_SCORE` to Settings

### P1 — Database Foundation + Auth
**3 days · 9 steps** — v4 steps 1.1–1.8 unchanged, plus:

#### 1.9 Migration 003 — TripEditEvent (v5)
- `trips/models.py` — `TripEditEvent` table
- Index: `TripEditEvent.trip_id`
- ✅ `alembic upgrade head` → TripEditEvent visible

### P2 — Geo Foundation
**4 days · 8 steps** — v4 steps 2.1–2.7 unchanged, plus:

#### 2.8 destinations/readiness + endpoint (v5)
- `destinations/readiness.py` — pure `compute_readiness()`
- `DestinationService.get_readiness(destination_id)` — aggregates counts from Place repo + Qdrant
- `GET /api/v1/destinations/{id}/readiness`
- 🚨 Qdrant unavailable → `indexed_pct=0`, score still computed, tier may be `limited`
- ✅ Darjeeling seeded → `score >= 0.7`, `tier=ready`

### P3 — Place Knowledge Layer
**3 days · 5 steps** — same as v4 (3.1–3.5)

### P4 — Travel Engine
**5 days · 8 steps** — v4 steps 4.1–4.6, plus:

#### 4.1 (updated) travel_engine/protocols.py (v5)
- Define `RoutingProvider`, `RouteLeg`, `TravelTimeMatrix`
- ✅ Import from travel_engine without geo dependency

#### 4.4 (updated) route_optimizer.py (v5)
- Accept injected `RoutingProvider` — remove any `geo/` import
- ✅ Unit test with `FakeRoutingProvider` — no network

#### 4.7 schedule_builder.py (v5)
- `build_day_schedule(ordered_stops, route_legs, rules) → list[ScheduledStop]`
- Morning-only enforcement, lunch break insertion
- ✅ 6-stop day → all `suggested_start_time` set, first stop >= `08:00`, morning viewpoint in slot 1 or 2

#### 4.8 planner/routing_provider.py + tools/registry stub (v5)
- `OsrmRoutingProvider` wraps `geo/osrm.py`
- `execute_tool()` skeleton with logging + `ToolResult` envelope
- ✅ Fake provider in tests; OSRM provider integration test optional

### P5 — Controlled Agent + Tools
**6 days · 12 steps**

#### 5.1 planner/tools/schemas.py + registry.py (v5)
- All tool I/O models + `ReplanAction` enum
- Register all six tools
- 🚨 Tool failure → `ToolResult(ok=False)` — never uncaught exception to graph

#### 5.2 Implement tools: check_readiness, search_places, rank_places (v5)
- `search_places` — Qdrant + PostGIS fallback, sets `used_geo_fallback`
- `rank_places` — delegates to `travel_engine.place_selector`
- ✅ Each tool tested in isolation with mocked ctx

#### 5.3 Implement tools: build_route, build_schedule, validate_itinerary (v5)
- `build_route` — day_allocator + route_optimizer with ctx.routing
- `build_schedule` — schedule_builder
- `validate_itinerary` — trip_validator
- ✅ build_route with FakeRoutingProvider → ordered stops

#### 5.4 planner/graph/state.py (v5)
- Full TravelState including base_lat/lng, replan fields, readiness_score
- ✅ TypedDict passes mypy/pyright check

#### 5.5 planner/graph/builder.py — hybrid graph (v5)
- Wire nodes per graph diagram above
- Conditional edge after validation → replan_supervisor OR END
- Conditional replan → route_planner OR validation based on action
- 🚨 Graph compiles at startup
- ✅ Happy path: replan_loop_count stays 0

#### 5.6 nodes/readiness_check.py (v5)
- Calls `execute_tool("check_readiness", ...)`
- Emits readiness warning into state if below threshold

#### 5.7 nodes/preference.py + clarification.py (v5)
- preference: unchanged LLM JSON parse via core/llm/client
- clarification: if `days` missing AND not parseable → set `needs_clarification=True`, SSE `clarification_needed` — **MVP: skip edge, use defaults**; wire fully in 5.12

#### 5.8 nodes/poi_retrieval, ranking, route_planner (v5)
- Each calls corresponding tool via execute_tool
- route_planner passes ctx.routing (OsrmRoutingProvider)

#### 5.9 nodes/schedule_builder.py (v5)
- Calls `build_schedule` tool after route ready
- SSE event `schedule_ready`

#### 5.10 nodes/itinerary.py (v5)
- LLM narrative only — must not alter stop order or times
- Validates LLM output does not contain place IDs not in state.route

#### 5.11 nodes/validation.py + replan_supervisor.py (v5)
- validation: trip_validator + record_generation with v5 eval fields
- replan_supervisor: LLM JSON → ReplanAction; increment replan_loop_count; execute action
- 🚨 max replans hit → ACCEPT_PARTIAL, abort_triggered=True, still record evaluation

#### 5.12 scripts/test_agent.py (v5)
- Assert happy path: replan_loop_count=0, all stops have suggested_start_time
- Assert replan path: inject bad itinerary → supervisor triggers ≤2 replans → final validation passes or warnings

### P6 — Planner API + Persistence
**3 days · 5 steps** — v4 steps 6.1–6.4 with updates:

#### 6.2 (updated) planner/router.py (v5)
- PlanRequest includes base_lat/lng
- SSE events include readiness_done, schedule_ready, replan_started
- Timeout from `PLANNER_GENERATION_TIMEOUT_SECONDS`
- Default base coords to destination center when omitted

#### 6.5 (updated) ship checklist (v5)
- [ ] All v4 checklist items still pass
- [ ] `GET /api/v1/destinations/{id}/readiness` → tier + score
- [ ] Itinerary stops include `suggested_start_time` and `visit_duration_min`
- [ ] Happy-path generation: `replan_loop_count=0`, `abort_triggered=False`
- [ ] Injected validation failure triggers replan ≤ `PLANNER_MAX_REPLAN_ATTEMPTS`
- [ ] No `geo/` imports inside `travel_engine/`
- [ ] All planner tools invoked via `execute_tool()` — grep confirms

### P7 — Edit & Replan
**2 days · 4 steps**

#### 7.1 trips/service.py — edit operations (v5)
- `reorder_stops(trip_id, day, place_ids, user_id)`
- `remove_stop(...)`, `add_stop(...)`, `reoptimize_day(...)`
- Each calls travel_engine + tools with OsrmRoutingProvider; single transaction
- Calls `evaluation.service.record_edit()`
- 🚨 Validation fail → rollback, 422 with warnings

#### 7.2 trips/router.py — edit endpoints (v5)
- Four endpoints per P7 table
- ✅ Reorder day 1 → polyline + times updated, GeoJSON reflects change

#### 7.3 tests/trips/test_edit_replan.py (v5)
- Reorder, remove, add, reoptimize scenarios
- Ownership 403 case
- ✅ pytest green

#### 7.4 evaluation record_edit + quality linkage (v5)
- `user_edited=True` on linked TripEvaluation when edit events exist
- ✅ Edit trip → TripEditEvent row + evaluation flag updatable

---

## LLD Pattern Reference

| Pattern | Where used |
|---------|-----------|
| Modular Monolith | Overall structure |
| Gateway Pattern | `geo/*`, `core/llm/client.py` |
| Strategy Pattern | `RoutingProvider`, `embed_text()`, `chat_completion()` model param |
| Protocol / DI | `travel_engine` routing injection |
| Tool Registry | `planner/tools/registry.py` |
| Controlled Agent | Fixed pipeline + enum-bound replan supervisor |
| State Machine | `TravelState` through LangGraph |
| Chain of Responsibility | Middleware, `trip_validator` rules |
| Response Envelope | `ApiResponse[T]`, `PaginatedResponse[T]` |
| Unit of Work | Trip + TripPlace + edit in one transaction |
| Configuration Object | `travel_rules.py` |
| Null Object Pattern | `NoOpTracer` |

---

## Failure Boundary Summary

| Layer | Failure | Response |
|-------|---------|----------|
| All v4 rows | — | unchanged |
| Readiness score low | `< PLANNER_MIN_READINESS_SCORE` | Warning in SSE + state; generation continues |
| Tool execution | Any unhandled error inside tool | `ToolResult(ok=False)`; node applies named fallback |
| Replan supervisor LLM | `WandrLLMError` | `DROP_WEAKEST_STOP` then `ACCEPT_PARTIAL` |
| Replan loop exhausted | `replan_loop_count >= max` | `abort_triggered=True`, partial itinerary + warnings |
| Trip edit validation | Fails after mutation attempt | Transaction rollback, 422 `ErrorResponse` |
| Trip edit OSRM | Timeout | Haversine fallback for affected day polyline only |

---

## Package Install Order

Same as v4 — no new packages required for v5 features.

| Step | Package | Reason |
|------|---------|--------|
| 0.2 | `pydantic-settings` | Settings |
| 0.4 | `structlog` | Logging |
| 0.5 | `langfuse` | Tracing |
| 0.6 | `litellm` `tenacity` | LLM + retry |
| 0.10 | `fastapi` `uvicorn[standard]` | App server |
| 1.1 | `sqlalchemy[asyncio]` `asyncpg` | Async DB |
| 1.3 | `alembic` `geoalchemy2` | Migrations + PostGIS |
| 1.6 | `python-jose[cryptography]` | JWT |
| 1.7 | `httpx` | External HTTP |
| 3.1 | `qdrant-client` | Vector search |
| 3.2 | `sentence-transformers` | Embeddings |
| 5.4 | `langgraph` | Agent graph |
| 7.3 | `pytest` `pytest-asyncio` `pytest-mock` | Tests |

---

## Timeline Summary

| Phase | Days | Focus |
|-------|------|-------|
| P0 | 2 | Scaffold, LLM client, AGENT.md |
| P1 | 3 | DB, auth, TripEditEvent migration |
| P2 | 4 | Geo, places, **readiness** |
| P3 | 3 | Qdrant, embeddings, enrichment |
| P4 | 5 | travel_engine pure + schedule + routing DI |
| P5 | 6 | Tools, controlled agent, replan loop |
| P6 | 3 | SSE API, trips CRUD, ship |
| P7 | 2 | Edit & replan endpoints |
| **Total** | **~28 days** | Backend only — frontend blueprint separate |

---

## v4 → v5 Migration Notes (for implementers)

1. Do **not** copy v4 `iteration_guard` per-node pattern — use `replan_loop_count` only.
2. Move any `geo/osrm` import out of `travel_engine/` into `planner/routing_provider.py`.
3. Extend `PlanRequest` and itinerary schemas before wiring frontend map timeline UI.
4. v4 ship checklist is a subset of v5 §6.5 — run full v5 checklist before calling backend MVP done.
