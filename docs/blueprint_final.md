# Wandr — Backend Blueprint v6 (Definitive)
> Production-grade AI travel planner. Modular monolith. Thin vertical slices. Phase-gated tool-loop agent. Every step ends with a runnable proof.

**Supersedes:** `wandr_blueprint_v4.md`, `wandr_blueprint_v5.md`, `wandr_blueprint_v5_1_tool_loop.md`

---

## What's in this version

| Source | What was taken |
|--------|----------------|
| v4 | Full step-by-step phase detail, resilience contracts, project structure, LLD patterns, failure boundary table, package install order |
| v5 | Controlled hybrid agent fixes, `RoutingProvider` DI, `schedule_builder`, destination readiness, `PlanRequest` base coords, `ItineraryStop` with `suggested_start_time`, P7 Edit & Replan API, v5 TravelState fields, updated AGENT.md |
| v5.1 | Phase-gated tool-loop agent replaces per-node pipeline for P5; `chat_with_tools()`, `AgentPhase`, `PHASE_TOOLS`, replan tools, control tools, updated SSE events, v5.1 TravelState fields, 14-step P5 |

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
| 8 | **LLM provider is swappable** — all LLM calls go through `core/llm/client.py` only, never direct SDK imports |
| 9 | **Resilience is mandatory** — every external call has explicit timeouts, retry strategy, and a named fallback |
| 10 | **Controlled AI-assisted dev** — `AGENT.md` guardrails prevent uncontrolled Cursor output |
| 11 | **Structure from code, narrative from LLM** — itinerary geometry, order, and times never come from free-form LLM output |
| 12 | **Tools are typed contracts** — all planner tools have Pydantic input/output schemas; no ad-hoc dict plumbing |
| 13 | **Agent loops are bounded** — every tool-loop run has `max_tool_calls`, phase gating, and validate-before-finish; no unbounded ReAct |

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
- `travel_engine/` has NO LLM calls and NO network/DB I/O. Pure Python only. Routing times are injected via `RoutingProvider` from caller.
- `evaluation/` records every generation and every edit. Never skip this, even on partial failures.

### Resilience (non-negotiable)
- Every httpx call MUST have explicit connect_timeout and read_timeout set.
- Every external call MUST use tenacity retry. See Resilience Contracts table in blueprint.
- Every external call MUST have a named fallback. Never let an external failure raise a 500.
- LangGraph replan loop MUST check `replan_loop_count < max_replan_attempts` before entering replan path.
- The SSE stream MUST be wrapped in asyncio.wait_for with PLANNER_GENERATION_TIMEOUT_SECONDS ceiling (default 45s).

### Agent / tools (non-negotiable)
- Agent tool calls MUST use names from `TOOL_REGISTRY` only — never invent tools.
- Tool args MUST validate against the tool's Pydantic input schema before execution.
- All tool execution goes through `execute_tool(name, input, ctx)` — agent node never calls impl functions directly.
- `finish_plan` MUST NOT succeed until `validate_itinerary` returned `ok=True` OR `state.abort_triggered=True`.
- LLM never outputs place IDs, coordinates, stop order, or times — those come from travel_engine + tools only.
- Phase gating: agent node binds ONLY tools allowed for `state.agent_phase` — never expose full registry to LLM.
- On `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force transition to WRAP_UP phase (validate → narrative → finish).
- Narrative (`write_narrative`) runs OUTSIDE the tool loop — fixed node after agent loop completes.

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
├── AGENT.md                        # ★ AI coding guardrails — read before every Cursor session
├── alembic/                        # migrations only, no logic
├── alembic.ini
├── docker-compose.yml              # local dev infra only (never used in prod)
├── requirements.txt                # append-only, packages added at point of use
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
    ├── main.py                     # app factory, lifespan, router registration
    ├── config.py                   # Pydantic Settings — all env vars, one place
    │
    ├── core/                       # cross-cutting infrastructure, no business logic
    │   ├── llm/
    │   │   └── client.py           # ★ LiteLLM wrapper — ONLY entry point for all LLM calls
    │   ├── database/
    │   │   ├── base.py             # DeclarativeBase, UUIDMixin, TimestampMixin, SoftDeleteMixin
    │   │   ├── session.py          # async engine, connection pool, get_db() dependency
    │   │   └── base_repository.py  # Generic[M, ID] — CRUD + paginate implemented once
    │   ├── security/
    │   │   ├── jwt.py              # create_access_token, verify_token
    │   │   └── permissions.py      # require_auth, optional_auth FastAPI dependencies
    │   ├── middleware/
    │   │   ├── logging.py          # request_id, latency, structlog context binding
    │   │   └── rate_limit.py       # in-memory dev / Redis prod, same interface
    │   ├── observability/
    │   │   ├── logging.py          # structlog config — ConsoleRenderer dev, JSONRenderer prod
    │   │   └── tracing.py          # Langfuse lazy init, NoOpTracer if keys missing
    │   ├── pagination.py           # PageParams, PaginatedResponse[T], paginate()
    │   ├── responses.py            # ApiResponse[T], ErrorResponse
    │   └── exceptions.py           # WandrError hierarchy
    │
    ├── auth/
    │   ├── router.py               # /api/v1/auth/...
    │   ├── schemas.py
    │   ├── models.py               # User
    │   ├── repository.py
    │   ├── service.py
    │   ├── dependencies.py
    │   └── exceptions.py
    │
    ├── destinations/
    │   ├── router.py               # + GET /{id}/readiness
    │   ├── schemas.py              # + DestinationReadinessOut
    │   ├── models.py               # Destination (cached geocode result)
    │   ├── repository.py
    │   ├── service.py              # DB-first lookup, Nominatim fallback + compute_readiness()
    │   └── readiness.py            # ★ pure scoring logic
    │
    ├── places/
    │   ├── router.py
    │   ├── schemas.py
    │   ├── models.py               # Place with PostGIS POINT column
    │   ├── repository.py           # upsert_from_poi, find_within_radius, list_paginated
    │   └── service.py              # enrich_place (LLM summary + tags via core/llm/client.py)
    │
    ├── trips/
    │   ├── router.py               # CRUD + /geojson + edit/replan endpoints (P7)
    │   ├── schemas.py              # + ReorderStopsIn, AddStopIn, TripEditOut
    │   ├── models.py               # Trip, TripPlace, TripEditEvent
    │   ├── repository.py
    │   ├── service.py              # save_from_state, build_geojson, reorder/remove/add/reoptimize
    │   └── exceptions.py
    │
    ├── planner/
    │   ├── router.py               # POST /generate (SSE)
    │   ├── schemas.py              # PlanRequest (+ base_lat/lng), PlanResult, ItineraryDay, ItineraryStop
    │   ├── service.py              # cache-aside wrapper + SSE event bridge
    │   ├── routing_provider.py     # ★ OsrmRoutingProvider implements RoutingProvider protocol
    │   ├── tools/                  # ★ typed tool layer — nodes call execute_tool() only
    │   │   ├── registry.py         # TOOL_REGISTRY, execute_tool(), get_tools_for_phase()
    │   │   ├── schemas.py          # Tool I/O Pydantic models, AgentPhase, ToolContext, ToolResult
    │   │   ├── check_readiness.py
    │   │   ├── search_places.py
    │   │   ├── rank_places.py
    │   │   ├── build_route.py
    │   │   ├── build_schedule.py
    │   │   ├── validate_itinerary.py
    │   │   ├── finish_plan.py
    │   │   ├── ask_clarification.py
    │   │   ├── reoptimize_routes.py
    │   │   ├── drop_weakest_stop.py
    │   │   ├── expand_poi_search.py
    │   │   └── accept_partial.py
    │   └── graph/
    │       ├── state.py
    │       ├── builder.py          # agent ↔ tool_executor loop + fixed bookend nodes
    │       ├── messages.py         # build_agent_messages — system prompt + tool results history
    │       └── nodes/
    │           ├── parse_preferences.py   # fixed LLM call before loop
    │           ├── agent.py               # ★ chat_with_tools — picks tool from PHASE_TOOLS
    │           ├── tool_executor.py       # ★ execute_tool + phase transitions
    │           ├── write_narrative.py     # fixed LLM call after loop — outside loop
    │           └── record_evaluation.py
    │
    ├── travel_engine/              # ★ travel intelligence layer — pure Python, no LLM, no I/O
    │   ├── travel_rules.py         # constants: max places/day, durations, weights, time rules
    │   ├── protocols.py            # ★ RoutingProvider, RouteLeg, TravelTimeMatrix protocols
    │   ├── place_selector.py       # which places? why? what gets excluded?
    │   ├── day_allocator.py        # how many days? how many places per day?
    │   ├── route_optimizer.py      # accepts RoutingProvider — never imports geo/
    │   ├── schedule_builder.py     # ★ morning slots, visit durations → suggested_start_time
    │   └── trip_validator.py       # is this a realistic, good trip?
    │
    ├── evaluation/
    │   ├── models.py               # TripEvaluation + TripEditEvent linkage
    │   ├── repository.py
    │   ├── service.py              # record_generation(), record_edit()
    │   └── schemas.py
    │
    ├── geo/
    │   ├── geocoder.py             # Gateway: Nominatim async client
    │   ├── overpass.py             # Gateway: POI scraper — seed scripts only
    │   ├── osrm.py                 # Gateway: routing + polylines, haversine fallback
    │   └── schemas.py              # GeocodedPlace, RawPOI, RouteResult
    │
    └── search/
        ├── client.py               # get_qdrant_client() singleton, ensure_collection()
        ├── embeddings.py           # embed_text(), embed_batch()
        └── places_index.py         # upsert_place(), search_places()
```

---

## Environment Variables

```bash
# Core
ENVIRONMENT=development          # development | production
DEBUG=true
SECRET_KEY=                      # long random string, never hardcoded

# Database
DATABASE_URL=                    # local: postgresql+asyncpg://...  prod: Neon/Supabase URL

# Vector search
QDRANT_URL=http://localhost:6333 # prod: https://xxx.qdrant.io
QDRANT_API_KEY=                  # empty for local, required for Qdrant Cloud

# Cache (optional — features degrade gracefully if missing)
REDIS_URL=                       # empty in dev (in-memory fallback), prod: Upstash URL

# LLM — provider-agnostic via LiteLLM
LLM_MODEL=nvidia_nim/meta/llama-3.1-8b-instruct   # or: groq/llama3-8b-8192, openai/gpt-4o-mini
LLM_API_KEY=
LLM_API_BASE=                    # optional: required for NVIDIA NIM custom base URL
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=4

# Planner agent bounds
PLANNER_MAX_TOOL_CALLS=12              # hard ceiling — every execute_tool increments tool_loop_count
PLANNER_MAX_REPLAN_ATTEMPTS=2          # replan_loop_count ceiling — NOT per tool call
PLANNER_GENERATION_TIMEOUT_SECONDS=45  # SSE asyncio.wait_for ceiling
PLANNER_MIN_READINESS_SCORE=0.3        # below this → warning in SSE, generation still allowed
PLANNER_AGENT_PHASE_STUCK_LIMIT=3      # same phase with no state change → auto-advance or abort

# Observability
LANGFUSE_PUBLIC_KEY=             # optional — NoOpTracer used if missing
LANGFUSE_SECRET_KEY=

# Geo
NOMINATIM_USER_AGENT=wandr-dev-yourname@email.com
OSRM_BASE_URL=https://router.project-osrm.org       # prod: self-hosted or Valhalla
```

**Production mapping:**

| Dev | Prod |
|-----|------|
| Local Postgres (Docker) | Neon / Supabase / Railway |
| Local Qdrant (Docker) | Qdrant Cloud free tier |
| No Redis | Upstash free tier |
| Console logs | Logtail / Datadog (JSONRenderer, zero config change) |
| Public OSRM | Self-hosted OSRM or Valhalla |
| NVIDIA NIM free tier | Swap `LLM_MODEL` env var only |

---

## Resilience Contracts
> **Non-negotiable implementation requirements. Cursor must not simplify these away.**
> Reference this table when implementing any external call. The values here are law.

| Component | Retry Strategy | Timeouts | 429 Handling | Final Fallback |
|---|---|---|---|---|
| `geo/geocoder.py` | tenacity 3x, exponential wait 1–8s | connect=5s, read=10s, total=15s | N/A | return `None` → caller raises `DestinationNotFound` |
| `geo/overpass.py` | tenacity 3x, exponential wait 2–16s | connect=10s, read=30s | N/A | return `[]` → seed script logs and continues |
| `geo/osrm.py` | tenacity 2x, fixed wait 1s | connect=5s, read=10s | N/A | haversine straight-line × 1.4 factor |
| `core/llm/client.py` (`chat_completion`) | tenacity 4x, exponential wait 2–30s | per-call=`LLM_TIMEOUT_SECONDS` | read `Retry-After` header, sleep before retry | raise `WandrLLMError(code="llm_unavailable")` |
| `core/llm/client.py` (`chat_with_tools`) | same contract as `chat_completion` | `LLM_TIMEOUT_SECONDS` | same | default tool for phase; then `abort_triggered` |
| LangGraph total | no retry | `PLANNER_GENERATION_TIMEOUT_SECONDS` | N/A | emit SSE `error` event, close stream cleanly |
| Tool loop (total) | no graph-level retry | bounded by `PLANNER_MAX_TOOL_CALLS` | N/A | force WRAP_UP → partial itinerary |
| LangGraph replan | bounded | N/A | N/A | `replan_loop_count >= max` → ACCEPT_PARTIAL → WRAP_UP |
| `planner/tools/*` | inherit callee contract | inherit | inherit | `ToolResult(ok=False, fallback_used=True)` — never raises |
| `tool_executor` | inherits per-tool | — | — | `ToolResult(ok=False)` — never raises to graph |
| Phase stuck detector | N/A | 3 iterations no state change | N/A | auto-advance phase OR `abort_triggered` |
| `search/places_index.py` | no retry | N/A | N/A | return `[]` → planner uses PostGIS radius fallback |

**Retry only on:** `httpx.TimeoutException`, `httpx.ConnectError`, `litellm.Timeout`, `litellm.RateLimitError`
**Never retry on:** 404, 422, 400, or any client error — these are bugs, not transient failures.

---

## core/llm/client.py — Design
> **This is the only file in the entire codebase that imports litellm. No exceptions.**

```python
# src/core/llm/client.py
# Gateway + Strategy Pattern.
# All callers use chat_completion() or chat_with_tools() — they never know which provider is active.

from litellm import acompletion, RateLimitError, Timeout as LLMTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from src.config import get_settings
from src.core.exceptions import WandrLLMError

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception_type((LLMTimeout, RateLimitError)),
    reraise=False,
)
async def chat_completion(messages, model=None, response_format=None) -> str:
    settings = get_settings()
    try:
        response = await acompletion(
            model=model or settings.LLM_MODEL,
            messages=messages,
            response_format=response_format,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content
    except RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e


@retry(...)  # same contract as chat_completion
async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],           # OpenAI-style tool schemas from registry.get_tools_for_phase()
    tool_choice: str = "auto",   # "auto" | "required" | "none"
    model: str | None = None,
) -> LLMToolResponse:
    """
    Returns LLMToolResponse with either:
      - tool_calls: list[{name, arguments_json}]
      - content: str (if model responded without tools)
    Raises WandrLLMError after retries exhausted.
    """
```

**Rules:**
- Tool schemas are generated from Pydantic models in `planner/tools/schemas.py` — never hand-written JSON in nodes.
- Agent node passes **phase-filtered** schemas only via `get_tools_for_phase(state.agent_phase)`.
- `parse_preferences` and `write_narrative` use `chat_completion()` — not the tool loop.

**Usage in nodes:**
```python
# CORRECT
from src.core.llm.client import chat_completion, chat_with_tools

# WRONG — never do this anywhere
from groq import Groq          # ❌
import litellm                 # ❌
```

---

## API Contracts

### PlanRequest
```python
class PlanRequest(BaseModel):
    destination_id: UUID
    raw_input: str
    days: int | None = None              # optional; preference node may parse from raw_input
    base_lat: float | None = None        # accommodation / start point; defaults to destination center
    base_lng: float | None = None
    accommodation_label: str | None = None  # display only
```

### ItineraryStop
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

### SSE Event Sequence (POST /api/v1/planner/generate)
```
event: preferences_done     data: {"days":3,"interests":["photography","offbeat"],...}
event: phase_changed        data: {"phase":"plan"}
event: tool_started         data: {"tool":"search_places","loop":2,"phase":"discover"}
event: tool_done            data: {"tool":"search_places","ok":true,"ms":340,"count":36}
event: clarification_needed data: {"question":"How many days?"}   # if ask_clarification
event: validation_done      data: {"passed":false,"errors":[...]}
event: itinerary_done       data: {full ItineraryDay[] JSON}
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

### travel_rules.py
```python
MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30
MAX_DAILY_TRAVEL_MIN = 180
DAY_START_TIME = "08:00"
LUNCH_BREAK_START = "13:00"
LUNCH_BREAK_MIN = 60
VISIT_DURATION_BY_CATEGORY = {
    "monastery": 45, "viewpoint": 20, "museum": 60,
    "trek": 180, "park": 30, "cultural": 45,
}
CATEGORY_WEIGHTS = {
    "photography": 1.4, "offbeat": 1.3, "viewpoint": 1.2,
    "trek": 1.1, "cultural": 1.0, "family": 0.9,
}
MORNING_ONLY_CATEGORIES = ["viewpoint", "sunrise_point"]
AVOID_SAME_DAY_PAIRS = [("monastery", "monastery")]
```

### place_selector.py
Answers: *which places? why? what gets excluded?*
- Filter by interest tags and budget
- Apply exclusion rules (sunrise viewpoints cannot be afternoon slots)
- Score with `CATEGORY_WEIGHTS`
- Remove `AVOID_SAME_DAY_PAIRS` conflicts
- `explain_selection(place, score_breakdown) → str` — logged to evaluation

### day_allocator.py
Answers: *how many places per day? how long at each?*
- Realistic visit duration from `VISIT_DURATION_BY_CATEGORY`
- Cap day load by 8hr active budget
- Geographic pre-clustering: places within 10km radius seeded into same-day candidate pool

### route_optimizer.py
Answers: *what order? how much travel time?*
- Signature: `optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider) → list[OrderedStop]`
- Calls `routing.travel_matrix()` — never imports `geo/`
- If total travel > `MAX_DAILY_TRAVEL_MIN` → drop lowest-scored stop, retry (max 3 attempts)
- Capped at 3 drop attempts; returns best available + warning if still over budget

### schedule_builder.py (new in v5)
Answers: *what time should each stop start?*
- Input: ordered stops + `RouteLeg` travel times + `VISIT_DURATION_BY_CATEGORY`
- Morning-only categories forced into slots 1–2 with `suggested_start_time <= "10:30"`
- Inserts lunch break at `LUNCH_BREAK_START` if day spans it
- Output: stops enriched with `visit_duration_min`, `suggested_start_time`, `arrival_note`
- Pure function — no LLM

### trip_validator.py
Answers: *is this a good, realistic trip?*
- Total daily travel < `MAX_DAILY_TRAVEL_MIN`
- No place repeated across days
- Morning-only places in morning slots (order ≤ 2)
- At least one "anchor" attraction per day (score > 0.7)
- Geographic coherence: std deviation of day's coordinates < threshold
- Returns `ValidationResult(passed, warnings, errors)`

---

## planner/tools — Design
> Typed tool layer. Nodes call `execute_tool()` only. Never call tool impl functions directly.

### AgentPhase
```python
class AgentPhase(str, Enum):
    DISCOVER  = "discover"    # readiness, search, rank
    PLAN      = "plan"        # build_route, build_schedule
    VALIDATE  = "validate"    # validate_itinerary
    REPLAN    = "replan"      # replan tools — entered when validation fails
    WRAP_UP   = "wrap_up"     # finish_plan only → exits to write_narrative
```

### Phase Transitions (deterministic — never LLM-chosen)

| From | Condition | To |
|------|-----------|-----|
| DISCOVER | `rank_places` succeeded | PLAN |
| PLAN | `build_schedule` succeeded | VALIDATE |
| VALIDATE | `validate_itinerary` ok=True | WRAP_UP |
| VALIDATE | errors AND `replan_loop_count < max` | REPLAN |
| VALIDATE | errors AND replan exhausted | WRAP_UP (`abort_triggered=True`) |
| REPLAN | any replan tool succeeded | PLAN (re-validate next loop) |
| REPLAN | `accept_partial` OR replan max hit | WRAP_UP |
| Any | `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` | WRAP_UP (`abort_triggered=True`) |
| DISCOVER | `ask_clarification` called | END (needs_input) |

### Tools Exposed to LLM Per Phase
```python
PHASE_TOOLS = {
    AgentPhase.DISCOVER:  ["check_readiness", "search_places", "rank_places", "ask_clarification"],
    AgentPhase.PLAN:      ["build_route", "build_schedule"],
    AgentPhase.VALIDATE:  ["validate_itinerary"],
    AgentPhase.REPLAN:    ["reoptimize_routes", "drop_weakest_stop", "expand_poi_search", "accept_partial"],
    AgentPhase.WRAP_UP:   ["finish_plan"],
}
```

### Full Tool Registry

| Tool | Phase | Notes |
|------|-------|-------|
| `check_readiness` | DISCOVER | Reads place/enrich/index counts; warns if score < threshold |
| `search_places` | DISCOVER | Qdrant + PostGIS fallback; sets `used_geo_fallback` |
| `rank_places` | DISCOVER | Delegates to `travel_engine.place_selector` |
| `build_route` | PLAN | day_allocator + route_optimizer with ctx.routing |
| `build_schedule` | PLAN | `travel_engine.schedule_builder` |
| `validate_itinerary` | VALIDATE | `travel_engine.trip_validator` |
| `finish_plan` | WRAP_UP | Sets `plan_complete=True`; precondition: validate ok OR abort |
| `ask_clarification` | DISCOVER | Sets `needs_clarification=True`; SSE event; exits loop |
| `reoptimize_routes` | REPLAN | Re-runs `build_route` + `build_schedule` for all days |
| `drop_weakest_stop` | REPLAN | Removes lowest-scored stop on worst day, re-routes |
| `expand_poi_search` | REPLAN | top_k × 1.5, re-search → rank → route → schedule |
| `accept_partial` | REPLAN | Sets `abort_triggered=True`, moves to WRAP_UP |

### registry.py
```python
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # each entry has: fn, input_model, output_model, allowed_phases, preconditions
}

def get_tools_for_phase(phase: AgentPhase) -> list[dict]:
    """OpenAI function schemas for LiteLLM — filtered by phase."""

async def execute_tool(name: str, input: BaseModel, ctx: ToolContext) -> ToolResult:
    # 1. Validate name in registry
    # 2. Validate phase allows tool
    # 3. Check preconditions → ToolResult(ok=False, code="precondition_failed") if fail
    # 4. Run tool fn inside try/except → never raise to graph
    # 5. Append to state.tool_trace
    # 6. Increment state.tool_loop_count
    # 7. Return ToolResult
```

### ToolContext
```python
class ToolContext(BaseModel):
    destination_id: UUID
    base_lat: float
    base_lng: float
    routing: RoutingProvider        # OsrmRoutingProvider injected from planner service
    db: AsyncSession
    state: TravelState              # read/write allowed fields only via typed helpers
```

---

## Phase-Gated Tool Loop — Agent Graph Design

```
START
  → parse_preferences          # single chat_completion — NOT in tool loop
  → agent                      # chat_with_tools — picks one tool from PHASE_TOOLS[phase]
  → tool_executor              # execute_tool — updates state, checks phase transition
  → [plan_complete OR needs_clarification OR abort?]
        needs_clarification → END
        plan_complete       → write_narrative → record_evaluation → END
        else                → agent (loop)
```

**Removed vs v5 hybrid:** separate nodes `readiness_check`, `poi_retrieval`, `ranking`, `route_planner`, `schedule_builder`, `replan_supervisor` — replaced by the agent + tool_executor loop.

**Fixed nodes (outside loop):**
- `parse_preferences` — one LLM JSON call, deterministic defaults on failure
- `write_narrative` — one LLM call; **cannot modify** stops, times, or order
- `record_evaluation` — always runs, even on abort

### nodes/agent.py
```python
async def agent_node(state: TravelState, ctx: ToolContext) -> TravelState:
    if state.tool_loop_count >= settings.PLANNER_MAX_TOOL_CALLS:
        state.abort_triggered = True
        state.agent_phase = AgentPhase.WRAP_UP
        return state

    tools = get_tools_for_phase(state.agent_phase)
    response = await chat_with_tools(
        messages=build_agent_messages(state),
        tools=tools,
    )

    if response.tool_calls:
        state.pending_tool_calls = response.tool_calls
    else:
        # Model replied without tool — nudge retry once, then deterministic default tool for phase
        state.warnings.append("agent_no_tool_call")
    return state
```

### nodes/tool_executor.py
```python
async def tool_executor_node(state: TravelState, ctx: ToolContext) -> TravelState:
    for call in state.pending_tool_calls:
        input_model = parse_tool_input(call.name, call.arguments_json)
        result = await execute_tool(call.name, input_model, ctx)
        apply_tool_result(state, result)
        maybe_transition_phase(state, call.name, result)
    state.pending_tool_calls = []
    return state
```

### Deterministic Fallback When Agent Misbehaves

| Situation | Fallback |
|-----------|----------|
| No tool call after nudge | Call default tool for current phase (DISCOVER → `check_readiness`) |
| Invalid tool for phase | Ignore; return `ToolResult(precondition_failed)` to agent message history |
| `WandrLLMError` in agent | Execute default tool chain for phase once; increment `llm_retry_count` |
| Same phase, no state change × 3 | Auto-advance phase OR `abort_triggered` |

### TravelState
```python
# Input
destination_id: UUID
destination_name: str
destination_lat: float
destination_lng: float
raw_input: str
session_id: str
base_lat: float                       # accommodation / start; defaults to destination center
base_lng: float

# Parsed prefs (from parse_preferences node)
days: int
budget: str
interests: list[str]
include_offbeat: bool
include_trekking: bool

# Agent loop (v5.1)
agent_phase: AgentPhase = AgentPhase.DISCOVER
tool_loop_count: int = 0
pending_tool_calls: list[PendingToolCall] = []
tool_trace: list[ToolTraceEntry] = []     # {name, ok, ms, phase, code?, fallback_used?}
plan_complete: bool = False
needs_clarification: bool = False
clarification_question: str | None = None

# Resilience signals
replan_loop_count: int = 0            # increments on REPLAN phase entry only
max_replan_attempts: int              # from settings.PLANNER_MAX_REPLAN_ATTEMPTS
abort_triggered: bool = False
llm_retry_count: int = 0
used_geo_fallback: bool = False
used_osrm_fallback: bool = False
readiness_score: float | None = None

# Working data
candidate_pois: list
ranked_pois: list
route: list
schedule: list
itinerary: dict                       # populated in write_narrative from schedule + route
validation_result: ValidationResult | None

# Output
errors: list[str]
warnings: list[str]
trace_id: str
```

---

## destinations/readiness — Design

### readiness.py
```python
def compute_readiness(
    place_count: int,
    enriched_count: int,      # places with non-null summary
    indexed_count: int,       # places in Qdrant (0 if search unavailable)
    search_available: bool,
) -> ReadinessResult:
    # score 0.0–1.0 weighted: place_count (0.4), enriched_pct (0.35), indexed_pct (0.25)
    # tier: "ready" >= 0.7, "limited" >= 0.3, "sparse" < 0.3
```

### GET /api/v1/destinations/{id}/readiness
```python
class DestinationReadinessOut(BaseModel):
    destination_id: UUID
    score: float
    tier: Literal["ready", "limited", "sparse"]
    place_count: int
    enriched_pct: float
    indexed_pct: float
    message: str | None   # e.g. "Limited POI data — results may be generic"
```

`check_readiness` tool in planner calls this; if `score < PLANNER_MIN_READINESS_SCORE`, adds SSE warning — **does not block generation**.

---

## evaluation — Design

### TripEvaluation
```python
class TripEvaluation:
    id: UUID
    trip_id: UUID | None
    destination_id: UUID

    # Input
    raw_input: str
    parsed_preferences: dict

    # Pipeline
    candidates_retrieved: int
    candidates_after_ranking: int

    # Output
    final_route: dict
    places_per_day: list[int]
    total_distance_km: float
    base_lat: float
    base_lng: float

    # Performance
    generation_time_ms: int
    token_usage: dict
    llm_model: str
    llm_retry_count: int

    # Agent loop signals
    tool_loop_count: int
    tool_trace: list[dict]              # serialized ToolTraceEntry[]
    agent_phase_reached: str            # last phase before finish/abort
    readiness_score: float | None

    # Resilience signals
    used_geo_fallback: bool
    used_osrm_fallback: bool
    abort_triggered: bool

    # Quality signals (filled later)
    validation_passed: bool
    validation_warnings: list[str]
    user_saved: bool
    user_edited: bool

    created_at: datetime
```

### TripEditEvent
```python
class TripEditEvent:
    id: UUID
    trip_id: UUID
    edit_type: Literal["reorder", "remove_stop", "add_stop", "reoptimize_day"]
    day_number: int | None
    place_id: UUID | None
    payload: dict               # before/after snapshot
    created_at: datetime
```

### Quality Signal Interpretation
- `user_saved=True` + `validation_passed=True` = good trip
- `user_edited=True` = something was wrong — which places got removed?
- High `tool_loop_count` near ceiling → agent struggling; tighten prompts or phase defaults
- Repeated `precondition_failed` in `tool_trace` → agent prompt or phase tool list bug
- `expand_poi_search` in trace often → destination data or ranking issue
- High `llm_retry_count` = rate limit pressure for that destination
- `abort_triggered=True` = ceiling hit — investigate immediately
- `used_geo_fallback=True` consistently = Qdrant reliability issue

---

## P7 — Edit & Replan API

| Method | Path | Body | Behavior |
|--------|------|------|----------|
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` | Reorder `TripPlace.order_in_day`; re-run `build_schedule` + OSRM polyline for day; record edit |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | — | Remove stop; re-optimize remaining day via `build_route` tool; record edit |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | `{ "place_id": uuid }` | Insert at end; re-optimize day; validate day load; record edit |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | — | Re-run route + schedule for day only; update polylines; record edit |

All endpoints: `require_auth` + ownership check → 403 on mismatch. Return `ApiResponse[TripOut]`. Validation failure after edit → 422 + transaction rollback, trip unchanged.

---

## Phase Blueprint

### Legend
- 📦 Package installed at this step
- 🏗️ LLD pattern
- 🚨 Failure boundary
- ☁️ Production consideration
- 🔒 Resilience contract applied

---

### P0 — Scaffold, Config & Core Conventions
**2 days · 10 steps**

#### 0.1 Repo + full directory skeleton
- Create entire folder tree. Empty `__init__.py` in each folder.
- Includes `travel_engine/`, `evaluation/`, `core/llm/`, `planner/tools/`, `travel_engine/protocols.py`, `destinations/readiness.py` from the start.
- Create `AGENT.md` at repo root (full content above). **This is step one — before any code.**
- 🏗️ **Modular Monolith** — each domain folder self-contained
- 🚨 Import failure at startup → clear module path in error, not silent 500
- ✅ `find src/ -type d | sort` → full tree, zero import errors. `cat AGENT.md` → guardrails visible.

#### 0.2 src/config.py — Pydantic Settings
- 📦 `pydantic-settings`
- `class Settings(BaseSettings)` — all env vars grouped by concern
- `@lru_cache def get_settings()` — loaded once per process
- Includes all vars from Environment Variables section above: `LLM_MODEL`, `LLM_API_KEY`, `LLM_TIMEOUT_SECONDS=20`, `LLM_MAX_RETRIES=4`, `PLANNER_MAX_TOOL_CALLS=12`, `PLANNER_MAX_REPLAN_ATTEMPTS=2`, `PLANNER_GENERATION_TIMEOUT_SECONDS=45`, `PLANNER_MIN_READINESS_SCORE=0.3`, `PLANNER_AGENT_PHASE_STUCK_LIMIT=3`
- 🏗️ **Singleton** — no re-parsing on every request
- ☁️ Dev reads `.env` file. Prod reads real env vars. Zero code change.
- 🚨 Missing required key at startup → `ValidationError` with field name, app refuses to start
- ✅ `python -c "from src.config import get_settings; print(get_settings().LLM_MODEL)"` → model string

#### 0.3 docker-compose.yml
- `postgis/postgis:16-3.4` with healthcheck + named volume
- `qdrant/qdrant:latest` port 6333 + named volume
- No Redis — `REDIS_URL` is `None` in dev, feature-flagged off
- ☁️ Prod has no docker-compose. All services are hosted APIs injected via env vars.
- 🚨 Postgres unhealthy → app lifespan logs "DB unreachable" and exits. No zombie process.
- ✅ `docker compose up -d` → both containers healthy

#### 0.4 core/observability/logging.py — structlog
- 📦 `structlog`
- Dev: `ConsoleRenderer`. Prod: `JSONRenderer`.
- `configure_logging()` called once in app lifespan
- 🏗️ **Context Propagation** — `bind_contextvars()` flows request_id through all log lines
- ☁️ JSONRenderer output pipes into Logtail/Datadog/CloudWatch with zero config change
- ✅ `structlog.get_logger().info("boot", env="dev")` → formatted log line

#### 0.5 core/observability/tracing.py — Langfuse
- 📦 `langfuse`
- `get_tracer() → Langfuse | NoOpTracer` — NoOpTracer has identical interface
- 🏗️ **Null Object Pattern** — callers never write `if tracer:` checks
- 🚨 Langfuse flush errors caught and logged as warnings — never propagate to user request
- ✅ `get_tracer().trace("test")` → no crash with or without keys

#### 0.6 core/llm/client.py — LiteLLM abstraction
- 📦 `litellm` `tenacity`
- `chat_completion()` + `chat_with_tools()` as designed above
- Reads all LLM settings from `get_settings()`
- tenacity: `stop_after_attempt(LLM_MAX_RETRIES)`, `wait_exponential(min=2, max=30)`
- On `RateLimitError`: read `Retry-After`, `asyncio.sleep(retry_after)`, re-raise for tenacity
- After all retries: raise `WandrLLMError(code="llm_unavailable")`
- Log every retry with: `model`, `attempt_number`, `wait_seconds`, `error_type`
- 🏗️ **Gateway Pattern** — single LLM entry point. Swap provider: change `LLM_MODEL` env var only.
- 🏗️ **Strategy Pattern** — `model` parameter allows per-call override
- 🔒 Resilience contract: see table above
- ✅ `await chat_completion([{"role":"user","content":"ping"}])` → string. Kill network → raises `WandrLLMError` after retries.

#### 0.7 core/pagination.py
- `PageParams`: page=1, size=20, max=100, computed offset
- `PaginatedResponse[T](BaseModel, Generic[T])`: items, total, page, size, pages, has_next, has_prev
- `paginate(result, total, params)` helper
- 🏗️ **Generic Repository** — every list endpoint typed and consistent
- ✅ `PaginatedResponse(items=[], total=55, page=1, size=20, pages=3)` → `has_next=True`

#### 0.8 core/responses.py
- `ApiResponse[T]`: success, data, message
- `ErrorResponse`: success=False, code, message, details
- 🏗️ **Response Envelope** — frontend has one error handler
- ✅ Both models serialise to clean JSON

#### 0.9 core/exceptions.py — WandrError hierarchy
- `WandrError(code, message, status_code, details)` base
- Subclasses: `NotFoundError(404)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ExternalServiceError(502)`, `WandrLLMError(503)`
- `WandrLLMError` — raised only by `core/llm/client.py`, caught only by agent/tool nodes
- 🏗️ **Exception Hierarchy** — single global handler catches all domain errors
- 🚨 Unhandled exceptions → full traceback logged server-side, generic `ErrorResponse` to client. No stack trace leakage.
- ✅ `raise WandrLLMError(code="llm_unavailable")` → caught → 503 `ErrorResponse`

#### 0.10 src/main.py — app factory + lifespan + /health
- 📦 `fastapi` `uvicorn[standard]`
- `create_app() → FastAPI` factory
- Lifespan: startup → configure_logging, DB ping, Qdrant ping. Shutdown → close pool.
- `GET /api/v1/health` → `{"status":"ok","env":"development","version":"1.0.0"}`
- 🏗️ **App Factory** — decouples creation from execution
- ☁️ `/health` used as liveness probe. Returns 503 if DB unreachable.
- 🚨 DB ping fails at startup → log critical + `exit(1)`.
- ✅ `uvicorn src.main:app` → `GET /api/v1/health` → 200 + structured log line

---

### P1 — Database Foundation + Auth
**3 days · 9 steps**

#### 1.1 core/database/base.py — declarative base + mixins
- 📦 `sqlalchemy[asyncio]` `asyncpg`
- `Base = DeclarativeBase()`
- `UUIDMixin`: `id = mapped_column(UUID, default=uuid4, primary_key=True)`
- `TimestampMixin`: created_at server_default, updated_at onupdate
- `SoftDeleteMixin`: deleted_at nullable — repos filter `deleted_at IS NULL` by default
- 🏗️ **Mixin Inheritance** — horizontal reuse
- ✅ `from src.core.database.base import Base, TimestampMixin` → no error

#### 1.2 core/database/session.py — async engine + pool
- `create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)`
- `async_sessionmaker(expire_on_commit=False)`
- `async def get_db() → AsyncSession` — yields, closes in finally
- 🏗️ **Unit of Work** — one session per request, shared transaction context
- ☁️ `pool_pre_ping=True` recycles stale connections on hosted Postgres idle drops
- 🚨 Connection timeout → `ExternalServiceError` 502
- ✅ `scripts/test_db_conn.py` → "PostgreSQL 16.x connected, pool ok"

#### 1.3 Alembic init + migration 001: PostGIS
- 📦 `alembic` `geoalchemy2`
- Configure `env.py` for async engine + Base metadata import
- Migration 001: `CREATE EXTENSION IF NOT EXISTS postgis`
- ☁️ Run `alembic upgrade head` as deploy step — never inside app startup
- ✅ `alembic upgrade head` → "Running upgrade → 001_enable_postgis"

#### 1.4 All core models — migration 002
- `auth/models.py` — User: id, email, name, avatar_url, google_id, is_active
- `places/models.py` — Place: id, osm_id(unique), name, category, tags(JSONB), summary, location(Geometry POINT 4326), destination_id
- `trips/models.py` — Trip: id, user_id(nullable), session_id, destination_id, days, preferences(JSONB), status(enum)
- `trips/models.py` — TripPlace: id, trip_id, place_id, day_number, order_in_day, travel_time_min, polyline
- `evaluation/models.py` — TripEvaluation (full schema above, including `tool_loop_count`, `tool_trace`, `used_geo_fallback`, `abort_triggered`)
- Indexes: `Place.osm_id`, `Place.destination_id`, `Trip.session_id`, `Trip.user_id`
- 🚨 Missing index on high-query columns = silent prod degradation. Add now.
- ✅ `alembic upgrade head` → all tables + indexes visible in `psql \dt \di`

#### 1.5 core/database/base_repository.py — generic repo base
- `class BaseRepository[M, ID]`
- Methods: `get_by_id()`, `create()`, `update()`, `soft_delete()`, `list_paginated(filters, params) → tuple[list[M], int]`
- `list_paginated` auto-applies `deleted_at IS NULL`
- 🏗️ **Generic Repository** + **Specification Pattern** — `filters: dict` not raw SQL
- ✅ Import without error

#### 1.6 core/security/jwt.py + permissions.py
- 📦 `python-jose[cryptography]`
- `create_access_token(user_id, email) → str` — HS256, 7-day expiry
- `verify_token(token) → TokenPayload | None` — returns None on invalid, never raises
- `require_auth` → raises `UnauthorizedError`. `optional_auth` → returns user or None.
- ☁️ SECRET_KEY in prod = long random string from env. Rotate by changing env var.
- 🚨 Expired token → 401. Malformed token → 401. Never 422 or 500.
- ✅ `verify_token(create_access_token(...))` → payload. `verify_token("bad")` → None

#### 1.7 auth/ — repository, service, router
- 📦 `httpx`
- `UserRepository(BaseRepository[User, UUID])`: `get_by_email()`, `get_by_google_id()`
- `AuthService`: `upsert_google_user()`, anonymous session UUID in httpOnly cookie
- `GET /api/v1/auth/google` → `GET /api/v1/auth/callback` → `GET /api/v1/auth/me` → `POST /api/v1/auth/logout`
- 🏗️ **Service Layer** — router calls service only
- 🚨 Google OAuth timeout → `ExternalServiceError` 502
- ✅ `GET /api/v1/auth/me` (no token) → `{"data":{"is_guest":true,"session_id":"uuid..."}}`

#### 1.8 core/middleware/logging.py
- Generate `X-Request-ID` per request, bind to structlog context
- Log `request.start` and `request.end` with latency_ms
- Return `X-Request-ID` in response headers
- 🏗️ **Chain of Responsibility** — middleware chain: request_id → logging → auth → rate_limit → handler
- ✅ `GET /api/v1/health` → response header `X-Request-ID` present + `request.end` log

#### 1.9 Migration 003 — TripEditEvent
- `trips/models.py` — `TripEditEvent` table (full schema from evaluation section)
- Index: `TripEditEvent.trip_id`
- ✅ `alembic upgrade head` → TripEditEvent visible

---

### P2 — Geo Foundation
**4 days · 8 steps**

#### 2.1 geo/geocoder.py — Nominatim client
- `geo/schemas.py`: `GeocodedPlace(name, lat, lng, osm_place_id, country, display_name)`
- `geocode(query) → GeocodedPlace | None` — async httpx, 1 req/sec rate limit, User-Agent from config
- httpx: `connect_timeout=5s`, `read_timeout=10s`, `timeout=15s`
- LRU cache on query string — same query never hits Nominatim twice in process
- 🏗️ **Gateway Pattern** — all geocoding through one module
- 🔒 Resilience contract: tenacity 3x, exponential 1–8s. After 3 failures → return None.
- ✅ `scripts/test_geocoder.py "Darjeeling"` → `GeocodedPlace(lat=27.041, lng=88.263)`. Kill network → returns None.

#### 2.2 geo/overpass.py — POI scraper
- `RawPOI(osm_id, name, lat, lng, category, raw_tags: dict)`
- OverpassQL: `tourism=attraction|viewpoint|museum|monastery` + `leisure=park` + `highway=trailhead`
- httpx: `connect_timeout=10s`, `read_timeout=30s`
- Filter: unnamed nodes discarded. Deduplicate by osm_id.
- 🏗️ **Gateway Pattern** — caller never constructs OverpassQL directly
- 🔒 Resilience contract: tenacity 3x, exponential 2–16s. After 3 failures → return `[]`.
- ✅ `scripts/test_overpass.py 27.041 88.263 30` → "Fetched 144 POIs"

#### 2.3 places/repository.py — upsert + radius + paginated
- `PlaceRepository(BaseRepository[Place, UUID])`
- `upsert_from_poi(poi, destination_id)` — `ON CONFLICT(osm_id) DO UPDATE`
- `find_within_radius(lat, lng, km)` — `ST_DWithin`
- `list_by_destination(destination_id, params)` — inherits paginate
- ✅ Insert 1 place, radius query finds it, paginated list returns it

#### 2.4 scripts/seed_destination.py
- Args: `--destination "Darjeeling" --radius 30`
- Geocode → Overpass → upsert places + Destination row
- Re-runnable (upsert). Progress per 10. Summary at end.
- 🚨 Single POI upsert fail → log + continue. Full seed never aborted for one bad record.
- ✅ `python scripts/seed_destination.py --destination "Darjeeling"` → "Seeded 144/144 places"

#### 2.5 geo/osrm.py — routing client
- `RouteResult(distance_km, duration_min, encoded_polyline)`
- `get_route(waypoints: list[tuple[float,float]]) → RouteResult`
- httpx: `connect_timeout=5s`, `read_timeout=10s`
- ☁️ Public OSRM for MVP. Prod: self-hosted OSRM or Valhalla via `OSRM_BASE_URL`.
- 🔒 Resilience contract: tenacity 2x, 1s fixed. Fallback → haversine × 1.4, log warning. Never fails user request.
- ✅ `get_route([(27.04,88.26),(27.03,88.27)])` → `RouteResult`. Kill OSRM → straight-line + log.

#### 2.6 destinations/ — repository, service, router
- `DestinationRepository(BaseRepository[Destination, UUID])`: `get_by_osm_place_id()`, `search_by_name()`
- `DestinationService.search(query)` — DB first, Nominatim on miss, save result
- `GET /api/v1/destinations/search?q=`
- 🏗️ **Cache-Aside** — check DB → miss → fetch external → write DB → return
- ✅ Two searches for "Darjeeling" → second has no Nominatim log line

#### 2.7 places/router.py — paginated list + single get
- `PlaceService`: `list_by_destination()`, `get_by_id()`
- `GET /api/v1/places?destination_id=&page=1&size=20` → `PaginatedResponse[PlaceOut]`
- `GET /api/v1/places/{id}` → `ApiResponse[PlaceOut]` or `NotFoundError` 404
- ✅ `GET /api/v1/places?destination_id=...&page=2&size=10` → `{"total":144,"page":2,"pages":15,"has_next":true}`

#### 2.8 destinations/readiness + endpoint
- `destinations/readiness.py` — pure `compute_readiness()` as designed above
- `DestinationService.get_readiness(destination_id)` — aggregates counts from Place repo + Qdrant
- `GET /api/v1/destinations/{id}/readiness` → `ApiResponse[DestinationReadinessOut]`
- 🚨 Qdrant unavailable → `indexed_pct=0`, score still computed, tier may be `limited`
- ✅ Darjeeling seeded → `score >= 0.7`, `tier=ready`

---

### P3 — Place Knowledge Layer
**3 days · 5 steps**

#### 3.1 search/client.py — Qdrant init
- 📦 `qdrant-client`
- `get_qdrant_client()` cached singleton
- `ensure_places_collection()` idempotent — vector size=384, cosine distance
- Called in app lifespan startup
- ☁️ Local: `QDRANT_URL=http://localhost:6333`. Prod: cloud URL + key.
- 🚨 Qdrant unreachable at startup → log warning, set `search_available=False`. Planner falls back to PostGIS. App still serves.
- 🚨 Embedding model load failure → log critical + `search_available=False`. Never `exit(1)`.
- ✅ App startup → "Qdrant collection 'places' ready (0 vectors)"

#### 3.2 search/embeddings.py — embed_text abstraction
- 📦 `sentence-transformers` — Model: `all-MiniLM-L6-v2` (384d, 80MB)
- `embed_text(text: str) → list[float]` — model loaded once at module level in try/except
- `embed_batch(texts: list[str]) → list[list[float]]`
- Model load failure sets `_model = None`, `embed_text` returns empty list, `search_available=False`
- 🏗️ **Strategy Pattern** — swap to OpenAI embeddings by changing one function body
- ✅ `embed_text("sunrise photography")` → list of 384 floats. Import with no GPU → degrades gracefully.

#### 3.3 places/service.py — enrich_place()
- `enrich_place(place) → EnrichedPlace(summary, tags)`
- Calls `core/llm/client.py:chat_completion()` with JSON mode
- Prompt: name + raw OSM tags → `{summary: str, tags: list[str]}`
- Tags from controlled vocab: `offbeat, photography, viewpoint, trek, monastery, cultural, family, nature, adventure`
- Skip if `place.summary` already set — re-runnable
- 🚨 `WandrLLMError` → log + skip place, continue batch
- ✅ `enrich_place(tiger_hill)` → `{"summary":"Tiger Hill is...","tags":["photography","viewpoint","sunrise"]}`

#### 3.4 search/places_index.py — upsert + semantic search
- `upsert_place(place)` — embeds summary+tags, stores with payload
- `search_places(query, destination_id, top_k) → list[PlaceSearchResult]`
- 🏗️ **Repository Pattern** — Qdrant treated as persistence layer
- 🚨 Qdrant search failure → catch, log, return `[]`. Planner uses PostGIS fallback.
- ✅ `search_places("photography sunrise", darjeeling_id, 10)` → Tiger Hill first

#### 3.5 scripts/enrich_places.py + scripts/index_places.py
- `enrich_places.py --destination Darjeeling` — batches of 10, progress, re-runnable
- `index_places.py --destination Darjeeling` — embeds all enriched places, upserts to Qdrant
- ✅ Both finish → "Indexed 144/144". Qdrant dashboard shows 144 vectors.

---

### P4 — Travel Engine (Intelligence Layer)
**5 days · 8 steps**

> Rules here. Logic here. Tools are thin wrappers. **No LLM calls. No external I/O. Pure Python only.**

#### 4.1 travel_engine/protocols.py
- Define `RoutingProvider`, `RouteLeg`, `TravelTimeMatrix` (full design above)
- ✅ Import from `travel_engine` without any `geo/` dependency

#### 4.2 travel_engine/travel_rules.py — constants + configuration
- All constants as in travel_engine design section
- 🏗️ **Configuration Object** — rules are data, not logic
- ✅ `from src.travel_engine.travel_rules import MAX_PLACES_PER_DAY` → 6

#### 4.3 travel_engine/place_selector.py
- `select_places(candidates, preferences, destination) → list[ScoredPlace]`
- Apply `CATEGORY_WEIGHTS`, exclusion rules, budget filter, conflict filter
- `explain_selection(place, score_breakdown) → str` — logged to evaluation
- 🏗️ **Strategy Pattern** — selection criteria configurable, testable in isolation
- ✅ 36 candidates, photography interests → photography places ranked higher, conflicts removed

#### 4.4 travel_engine/day_allocator.py
- `allocate_days(selected_places, days, preferences) → list[list[ScoredPlace]]`
- Time budget per day: 8hr − travel buffer
- Cap at `MAX_PLACES_PER_DAY`; geographic pre-clustering within 10km radius
- ✅ `allocate_days(18 places, 3)` → 3 lists, each ≤6 places, visit time < 8hrs

#### 4.5 travel_engine/route_optimizer.py (updated)
- `optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider) → list[OrderedStop]`
- Calls `routing.travel_matrix()` — never imports `geo/`
- Drop-retry loop capped at 3 attempts
- 🏗️ **Template Method** — algorithm skeleton with injectable routing
- ✅ Unit test with `FakeRoutingProvider` — no network required

#### 4.6 travel_engine/schedule_builder.py
- `build_day_schedule(ordered_stops, route_legs, rules) → list[ScheduledStop]`
- Morning-only enforcement, lunch break insertion
- ✅ 6-stop day → all `suggested_start_time` set, first stop >= "08:00", morning viewpoint in slot 1 or 2

#### 4.7 travel_engine/trip_validator.py
- `validate_trip(itinerary) → ValidationResult(passed, warnings, errors)`
- Rules: daily travel cap, no repeated places, morning slots, anchor per day, geo coherence
- 🏗️ **Chain of Responsibility** — each rule is a separate check function
- ✅ Good itinerary → `errors=[]`. Injected bad itinerary → specific error messages.

#### 4.8 planner/routing_provider.py + tools/registry stub
- `OsrmRoutingProvider` wraps `geo/osrm.py`, implements `RoutingProvider`
- Sets `state.used_osrm_fallback = True` when haversine used
- `execute_tool()` skeleton with logging + `ToolResult` envelope
- ✅ Fake provider in tests; OSRM integration test optional

---

### P5 — Phase-Gated Tool Loop Agent
**7 days · 14 steps**

> Complete steps 5.1–5.3 (tool implementations) first — the agent loop orchestrates existing tools.

#### 5.1 planner/tools/schemas.py + registry.py
- All tool I/O Pydantic models + `AgentPhase` enum + `ToolContext` + `ToolResult`
- `PHASE_TOOLS` mapping
- Register all 12 tools (6 core + 2 control + 4 replan)
- 🚨 Tool failure → `ToolResult(ok=False)` — never uncaught exception to graph
- ✅ `execute_tool` with wrong-phase tool → `precondition_failed` without execution

#### 5.2 Implement core six tools
- `check_readiness` — calls `destinations/readiness.py`, sets readiness_score in state
- `search_places` — Qdrant + PostGIS fallback, sets `used_geo_fallback`
- `rank_places` — delegates to `travel_engine.place_selector`
- ✅ Each tool tested in isolation with mocked ctx

#### 5.3 Implement replan + control tools
- `build_route` — day_allocator + route_optimizer with `ctx.routing`
- `build_schedule` — schedule_builder
- `validate_itinerary` — trip_validator
- `finish_plan`, `ask_clarification`, `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial`
- Each: Pydantic I/O, phase tag, precondition function
- ✅ `finish_plan` without prior validate → `precondition_failed`
- ✅ `build_route` with `FakeRoutingProvider` → ordered stops

#### 5.4 core/llm/client.py — `chat_with_tools()` addition
- Schema passthrough to LiteLLM `acompletion(tools=...)`
- Parse `tool_calls` from response; handle model returning content-only
- 🔒 Same retry contract as `chat_completion`
- ✅ Mock LiteLLM response with tool_call → parsed correctly

#### 5.5 registry — phase gating + preconditions
- `get_tools_for_phase(phase) → list[dict]` — OpenAI function schemas
- `check_preconditions(name, state) → bool`
- `maybe_transition_phase(state, tool_name, result)` — deterministic transitions per table
- `execute_tool` appends to `tool_trace`, increments `tool_loop_count`
- ✅ Wrong-phase tool rejected without execution

#### 5.6 planner/graph/state.py — TravelState
- Full TravelState TypedDict per design section above
- ✅ TypedDict passes mypy/pyright check

#### 5.7 planner/graph/messages.py — agent prompt
- System prompt: role, allowed tools for current phase, hard rules (never invent places)
- Compact state summary: days, interests, counts, last validation errors
- Include last 5 `tool_trace` entries as context — **not full history** (token control)

#### 5.8 nodes/parse_preferences.py
- `chat_completion()` with JSON mode — runs before loop, not in loop
- Parse: `{days, budget, interests, include_offbeat, include_trekking}`
- On `WandrLLMError`: sensible defaults (3 days, mid budget). Increment `llm_retry_count`. Never blocks.
- ✅ "3 days offbeat photography" → `state.days=3, state.interests=["photography","offbeat"]`. Kill LLM → defaults applied.

#### 5.9 nodes/agent.py + tool_executor.py
- `agent_node`: ceiling check → `get_tools_for_phase` → `chat_with_tools` → set `pending_tool_calls`
- `tool_executor_node`: parse input → `execute_tool` → `apply_tool_result` → `maybe_transition_phase`
- Deterministic fallbacks per table above
- ✅ DISCOVER → PLAN → VALIDATE → WRAP_UP on happy path
- ✅ `tool_loop_count` increments on every execute_tool call

#### 5.10 nodes/write_narrative.py + record_evaluation.py
- `write_narrative`: locked `state.schedule` + `state.route` structure — cannot be altered
- Calls `chat_completion()` — day titles + paragraph per day only
- Post-check: every `place_id` in LLM prompt must exist in schedule — LLM cannot add stops
- On `WandrLLMError` → template strings per day; increment `llm_retry_count`
- `record_evaluation`: persists `tool_trace`, `tool_loop_count`, `agent_phase_reached`, all v5 eval fields
- 🚨 Evaluation always written even on abort
- ✅ Evaluation row includes full `tool_trace` JSON

#### 5.11 planner/graph/builder.py — compile graph
- Wire: `parse_preferences → agent ↔ tool_executor` loop
- Conditional: `plan_complete → write_narrative → record_evaluation → END`
- Conditional: `needs_clarification → END`
- Else: loop back to agent
- 🚨 Graph compiles at startup — compilation error caught before first request
- ✅ Graph compiles; no orphan nodes

#### 5.12 planner/service.py — SSE bridge
- Map `execute_tool` hooks to emit `tool_started` / `tool_done` SSE events
- Map phase transitions to `phase_changed` SSE event
- 🔒 Wrapped in `asyncio.wait_for(..., PLANNER_GENERATION_TIMEOUT_SECONDS)`

#### 5.13 tests/planner/test_tool_loop.py
- Happy path: `tool_loop_count ≤ 8`, `plan_complete=True`, all stops have `suggested_start_time`
- Validation fail → REPLAN tools invoked → `replan_loop_count ≤ PLANNER_MAX_REPLAN_ATTEMPTS`
- Max tool calls → `abort_triggered=True`, partial itinerary, evaluation recorded
- `ask_clarification` → `needs_clarification=True`, loop exits early
- ✅ pytest green

#### 5.14 scripts/test_agent.py
- End-to-end Darjeeling via HTTP or direct graph invoke
- Input: `raw_input="3 days offbeat photography budget"`
- Assert: `errors=[]`, day count=3, all stops have `lat/lng` + `suggested_start_time`, `abort_triggered=False`
- Print `tool_trace` summary table to stdout
- Print Langfuse trace URL if keys configured
- ✅ Complete 3-day itinerary, "validation: passed", evaluation row written, `tool_trace` non-empty

---

### P6 — Planner API + Persistence
**3 days · 5 steps**

#### 6.1 trips/ — repository + service
- `TripRepository(BaseRepository[Trip, UUID])`: `list_by_user()`, `list_by_session()`, `get_with_places()`
- `TripService.save_from_state(state, user_id, session_id) → Trip`
- Anonymous trips claimable after login (session_id match)
- 🏗️ **Unit of Work** — Trip + TripPlace written in one transaction
- 🚨 Partial TripPlace insert fail → full rollback
- ✅ Save itinerary → `trip_id` returned → `get_with_places` → all stops present

#### 6.2 planner/router.py — POST /generate streaming SSE
- `POST /api/v1/planner/generate` body: `PlanRequest(destination_id, raw_input, days, base_lat, base_lng)`
- `StreamingResponse` content-type `text/event-stream`
- SSE events: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `error`, `clarification_needed`
- `optional_auth` — guests can plan, registered users get auto-save
- Default `base_lat/lng` to destination center when omitted
- 🔒 Wrapped in `asyncio.wait_for(graph.invoke(state), timeout=PLANNER_GENERATION_TIMEOUT_SECONDS)`
- 🚨 `asyncio.TimeoutError` → emit SSE `error` event, close stream. Never hangs.
- ✅ `curl -N POST /api/v1/planner/generate` → events stream. Stall at 46s → stream closes with error event.

#### 6.3 trips/router.py — CRUD + GeoJSON
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` (require_auth)
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` (optional_auth + ownership)
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public)
- `DELETE /api/v1/trips/{id}` → 204 (require_auth + ownership)
- 🚨 Accessing another user's trip → 403 (not 404)
- ✅ `GET /api/v1/trips/{id}/geojson` → paste to geojson.io → route renders on map

#### 6.4 core/middleware/rate_limit.py + planner cache
- Rate limiter: 10 req/min per IP on `/planner/generate`. Returns 429 + `Retry-After`.
- Planner cache key: `sha256(destination_id + sorted_interests + days + budget)` — 1hr TTL
- Dev: in-memory dict. Prod (REDIS_URL present): Redis SET.
- 🚨 Rate limiter error → fail open + log warning. Cache unavailable → skip cache, run agent fresh.
- ✅ Same input twice → 2nd response instant. 11th rapid request → 429.

#### 6.5 Backend Ship Checklist
- [ ] All errors return `ErrorResponse`. All lists return `PaginatedResponse`.
- [ ] `GET /api/v1/destinations/search?q=Darjeeling` → geocoded result
- [ ] `GET /api/v1/destinations/{id}/readiness` → tier + score
- [ ] `GET /api/v1/places?destination_id=...&page=2` → `PaginatedResponse` with `has_next/has_prev`
- [ ] `POST /api/v1/planner/generate` → SSE stream with `tool_started/tool_done` events, final `itinerary_done`
- [ ] `GET /api/v1/trips/{id}/geojson` → valid GeoJSON, renders on geojson.io
- [ ] Itinerary stops include `suggested_start_time` and `visit_duration_min`
- [ ] Happy-path: `replan_loop_count=0`, `abort_triggered=False`, `tool_loop_count ≤ 8`
- [ ] Injected validation failure → REPLAN tools invoked ≤ `PLANNER_MAX_REPLAN_ATTEMPTS`
- [ ] Max tool calls → `abort_triggered=True`, partial itinerary + SSE warnings
- [ ] `tool_trace` persisted on every generation
- [ ] Agent never calls tool outside current phase (integration test asserts)
- [ ] `finish_plan` blocked until validate ok or abort (unit test)
- [ ] `evaluation` table has rows with `tool_trace`, `tool_loop_count` after each generation
- [ ] `travel_engine` rules pass for Darjeeling + Manali + Goa
- [ ] `pytest tests/ -v` → all green
- [ ] `docker compose up` from clean state → works
- [ ] No hardcoded values — all from `get_settings()`
- [ ] grep: no `litellm`, `groq`, or `openai` imports outside `core/llm/client.py`
- [ ] grep: no direct `geo/` imports inside `travel_engine/`
- [ ] grep: no direct tool fn imports in `planner/graph/nodes/` — only `execute_tool`
- [ ] Kill LLM during agent loop → default tool fallback → clean error event
- [ ] Change `LLM_MODEL` env var → zero code changes needed

---

### P7 — Edit & Replan
**2 days · 4 steps**

#### 7.1 trips/service.py — edit operations
- `reorder_stops(trip_id, day, place_ids, user_id)`
- `remove_stop(...)`, `add_stop(...)`, `reoptimize_day(...)`
- Each calls `travel_engine` + tools with `OsrmRoutingProvider`; single transaction
- Calls `evaluation.service.record_edit()` → writes `TripEditEvent`
- 🚨 Validation fail → rollback, 422 with `details.validation_warnings`

#### 7.2 trips/router.py — edit endpoints
- Four endpoints per P7 table above
- All: `require_auth` + ownership → 403 on mismatch
- Return `ApiResponse[TripOut]` with updated itinerary slice
- ✅ Reorder day 1 → polyline + times updated, GeoJSON reflects change

#### 7.3 tests/trips/test_edit_replan.py
- Reorder, remove, add, reoptimize scenarios
- Ownership 403 case
- OSRM fail during reoptimize → haversine fallback, no 500
- ✅ pytest green

#### 7.4 evaluation record_edit + quality linkage
- `user_edited=True` on linked `TripEvaluation` when edit events exist
- ✅ Edit trip → `TripEditEvent` row + evaluation flag updatable

---

## LLD Pattern Reference

| Pattern | Where used |
|---------|-----------|
| Modular Monolith | Overall project structure |
| Singleton | `get_settings()`, `get_qdrant_client()`, `build_graph()` |
| App Factory | `create_app()` in main.py |
| Generic Repository | `BaseRepository[M, ID]` |
| Unit of Work | Session per request, Trip+TripPlace+edit in one transaction |
| Specification Pattern | `filters: dict` in repo queries |
| Service Layer | Router → Service → Repository only |
| Gateway Pattern | `geo/geocoder.py`, `geo/overpass.py`, `geo/osrm.py`, `core/llm/client.py` |
| Cache-Aside | Destinations lookup, planner result cache |
| Strategy Pattern | `RoutingProvider`, `embed_text()`, `chat_completion()` model param |
| Protocol / DI | `travel_engine` routing injection via `RoutingProvider` |
| Null Object Pattern | `NoOpTracer` |
| Response Envelope | `ApiResponse[T]`, `PaginatedResponse[T]` |
| Exception Hierarchy | `WandrError` → domain exceptions + `WandrLLMError` |
| Chain of Responsibility | Middleware stack, `trip_validator` rules |
| State Machine | `TravelState` through LangGraph |
| Builder Pattern | `build_graph()` |
| Configuration Object | `travel_rules.py` |
| Template Method | `route_optimizer` with injectable routing call |
| Tool Registry | `planner/tools/registry.py` |
| Phase-Gated Tool Loop | `agent` ↔ `tool_executor` with `PHASE_TOOLS` |
| Bounded ReAct | `tool_loop_count` + `PLANNER_MAX_TOOL_CALLS` |
| Tool Precondition | `registry.check_preconditions()` before every execute |
| Bookend Nodes | `parse_preferences` + `write_narrative` outside loop |

---

## Failure Boundary Summary

| Layer | Failure | Response |
|-------|---------|----------|
| DB connection | Timeout / unreachable | `ExternalServiceError` 502, pool_pre_ping recycles stale connections |
| DB migration | Failed migration | Auto-rollback, running app unaffected |
| Nominatim | Timeout / connect fail | tenacity 3x retry → return None → `DestinationNotFound` 404 |
| Overpass | Timeout / connect fail | tenacity 3x retry → return `[]` → seed script logs and continues |
| OSRM | Timeout | tenacity 2x retry → haversine × 1.4 fallback. Itinerary still valid. |
| Qdrant | Unreachable | `search_available=False`, PostGIS radius fallback. `used_geo_fallback=True`. |
| Embedding model load | OOM / corrupt cache | `search_available=False`, PostGIS fallback. App still starts. |
| LLM (any node) | Timeout | `core/llm/client.py`: tenacity 4x → `WandrLLMError` → node applies fallback |
| LLM (any node) | 429 Rate Limit | `core/llm/client.py` reads `Retry-After`, sleeps, retries. Never propagates 429. |
| LLM (parse_preferences) | `WandrLLMError` after retries | Sensible defaults. `llm_retry_count++`. Never blocks. |
| LLM (agent node) | `WandrLLMError` | Default tool chain for phase; `llm_retry_count++` |
| LLM (write_narrative) | `WandrLLMError` | Template strings per day; `llm_retry_count++` |
| LLM (enrichment) | `WandrLLMError` | Log + skip place, batch continues |
| Agent picks invalid tool | Not in registry | Skip call; error fed back to agent message history |
| Agent picks wrong-phase tool | Phase mismatch | `precondition_failed`; not executed |
| Agent no tool call | After nudge | Default tool for phase |
| `tool_loop_count >= max` | Ceiling hit | `abort_triggered=True`, force WRAP_UP, partial plan |
| Phase stuck × 3 | No state change | Auto-advance phase OR `abort_triggered` |
| `finish_plan` early | Validate not passed | `precondition_failed`; remain in loop |
| LangGraph total | Execution > `PLANNER_GENERATION_TIMEOUT_SECONDS` | `asyncio.TimeoutError` caught, SSE `error` event, stream closed |
| Readiness score low | `< PLANNER_MIN_READINESS_SCORE` | Warning in SSE + state; generation continues |
| Tool execution | Unhandled error inside tool | `ToolResult(ok=False)`; node applies named fallback |
| Replan loop exhausted | `replan_loop_count >= max` | `accept_partial` → `abort_triggered=True`, partial itinerary |
| Langfuse | Any error | Caught as warning. Never propagates. |
| JWT | Expired / malformed | 401 `ErrorResponse`. Never 422 or 500. |
| Auth callback | OAuth failure | Redirect to `/auth/error`. Never 500 page. |
| Rate limiter | Internal error | Fail open + log warning |
| Redis cache | Unavailable | Skip cache, run agent fresh |
| Trip save | Partial insert | Full transaction rollback. Trip never exists without its places. |
| Trip edit validation | Fails after mutation attempt | Transaction rollback, 422 `ErrorResponse` |
| Trip edit OSRM | Timeout | Haversine fallback for affected day polyline only |

---

## Package Install Order

| Step | Package | Reason |
|------|---------|--------|
| 0.2 | `pydantic-settings` | Settings class |
| 0.4 | `structlog` | Logging |
| 0.5 | `langfuse` | AI tracing |
| 0.6 | `litellm` `tenacity` | LLM abstraction + retry |
| 0.10 | `fastapi` `uvicorn[standard]` | App server |
| 1.1 | `sqlalchemy[asyncio]` `asyncpg` | Async DB |
| 1.3 | `alembic` `geoalchemy2` | Migrations + PostGIS |
| 1.6 | `python-jose[cryptography]` | JWT |
| 1.7 | `httpx` | External HTTP |
| 3.1 | `qdrant-client` | Vector search |
| 3.2 | `sentence-transformers` | Embeddings |
| 5.6 | `langgraph` | Agent graph |
| 7.3 | `pytest` `pytest-asyncio` `pytest-mock` | Tests |

**Removed:** `groq`, `langchain-groq` — replaced by `litellm` at step 0.6.

---

## Timeline Summary

| Phase | Days | Focus |
|-------|------|-------|
| P0 | 2 | Scaffold, LLM client (with tools), AGENT.md |
| P1 | 3 | DB, auth, TripEditEvent migration |
| P2 | 4 | Geo, places, readiness endpoint |
| P3 | 3 | Qdrant, embeddings, enrichment |
| P4 | 5 | travel_engine pure + protocols + schedule_builder + routing DI |
| P5 | 7 | Phase-gated tool loop agent |
| P6 | 3 | SSE API, trips CRUD, ship checklist |
| P7 | 2 | Edit & replan endpoints |
| **Total** | **~29 days** | Backend only — frontend map blueprint separate |

---

## Quick Reference: What the LLM Can and Cannot Do

| Can | Cannot |
|-----|--------|
| Choose next tool from phase allowlist | Invent tool names or args outside schema |
| Call `ask_clarification` when input ambiguous | Output place IDs, lat/lng, or stop order |
| Call replan tools when validation fails | Skip `validate_itinerary` before `finish_plan` |
| Write day titles and narrative (`write_narrative` node) | Change `suggested_start_time` or route geometry |

**Structure from code. Orchestration from agent. Narrative from LLM.**

Role: You are a senior principle backend engineer and lead product developer(you can take desicion , if the code base is going in a worng way )