# Wandr — Backend Blueprint v4
> Production-grade AI travel planner (map visualization based in frontend). Modular monolith. Thin vertical slices. Every step ends with a runnable proof.

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
- `travel_engine/` has NO LLM calls. Pure Python only. No external I/O.
- `evaluation/` records every generation. Never skip this, even on partial failures.

### Resilience (non-negotiable)
- Every httpx call MUST have explicit connect_timeout and read_timeout set.
- Every external call MUST use tenacity retry. See Resilience Contracts table in blueprint.
- Every external call MUST have a named fallback. Never let an external failure raise a 500.
- LangGraph graph MUST check iteration_count before every non-trivial node.
- The SSE stream MUST be wrapped in asyncio.wait_for with a 45s ceiling.

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
├── scripts/                        # one-off CLI tools, never imported by app
│   ├── seed_destination.py
│   ├── enrich_places.py
│   ├── index_places.py
│   └── test_agent.py
├── tests/
│   ├── conftest.py
│   ├── auth/
│   ├── planner/
│   ├── geo/
│   └── trips/
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
    │   └── exceptions.py           # WandrError hierarchy → NotFoundError, UnauthorizedError, WandrLLMError, etc.
    │
    ├── auth/                       # domain module
    │   ├── router.py               # /api/v1/auth/...
    │   ├── schemas.py
    │   ├── models.py               # User
    │   ├── repository.py           # extends BaseRepository
    │   ├── service.py              # google_oauth_flow, issue_jwt, anonymous_session
    │   ├── dependencies.py         # get_current_user, get_optional_user
    │   └── exceptions.py
    │
    ├── destinations/               # domain module
    │   ├── router.py               # /api/v1/destinations/search
    │   ├── schemas.py
    │   ├── models.py               # Destination (cached geocode result)
    │   ├── repository.py
    │   └── service.py              # DB-first lookup, Nominatim fallback
    │
    ├── places/                     # domain module
    │   ├── router.py               # /api/v1/places/
    │   ├── schemas.py
    │   ├── models.py               # Place with PostGIS POINT column
    │   ├── repository.py           # upsert_from_poi, find_within_radius, list_paginated
    │   └── service.py              # enrich_place (LLM summary + tags via core/llm/client.py)
    │
    ├── trips/                      # domain module
    │   ├── router.py               # /api/v1/trips/ CRUD + /geojson
    │   ├── schemas.py
    │   ├── models.py               # Trip, TripPlace
    │   ├── repository.py
    │   ├── service.py              # save_from_state, build_geojson, ownership check
    │   └── exceptions.py
    │
    ├── planner/                    # domain module — AI agent orchestration
    │   ├── router.py               # /api/v1/planner/generate (streaming SSE)
    │   ├── schemas.py              # PlanRequest, PlanResult, ItineraryDay
    │   ├── service.py              # cache-aside wrapper around graph.invoke()
    │   └── graph/
    │       ├── state.py            # TravelState TypedDict — single object through all nodes
    │       ├── builder.py          # build_graph() → CompiledGraph singleton + iteration_guard node
    │       └── nodes/
    │           ├── iteration_guard.py  # ★ hard ceiling — abort if max_iterations hit
    │           ├── preference.py       # parse raw input → structured prefs (LLM JSON mode)
    │           ├── poi_retrieval.py    # Qdrant semantic search + PostGIS fallback
    │           ├── ranking.py          # pure Python scorer — no LLM
    │           ├── route_planner.py    # calls travel_engine — no logic here
    │           ├── itinerary.py        # LLM narrative only — structure comes from travel_engine
    │           └── validation.py       # paranoid output checks before leaving agent
    │
    ├── travel_engine/              # ★ travel intelligence layer — destination-agnostic rules
    │   ├── travel_rules.py         # constants: max places/day, min travel buffer, category weights
    │   ├── place_selector.py       # which places? why? what gets excluded?
    │   ├── day_allocator.py        # how many days? how many places per day?
    │   ├── route_optimizer.py      # what order? how much travel time between stops?
    │   └── trip_validator.py       # is this a realistic, good trip?
    │
    ├── evaluation/                 # ★ trip quality data — stored from day one
    │   ├── models.py               # TripEvaluation — stores every generation event
    │   ├── repository.py
    │   ├── service.py              # record_generation(), get_quality_report()
    │   └── schemas.py              # EvalRecord, QualityReport
    │
    ├── geo/                        # infrastructure — external geo service wrappers
    │   ├── geocoder.py             # Gateway: Nominatim async client, tenacity retry, LRU cache
    │   ├── overpass.py             # Gateway: POI scraper — seed scripts only, tenacity retry
    │   ├── osrm.py                 # Gateway: routing + polylines, straight-line fallback
    │   └── schemas.py              # GeocodedPlace, RawPOI, RouteResult
    │
    └── search/                     # infrastructure — Qdrant wrapper
        ├── client.py               # get_qdrant_client() singleton, ensure_collection()
        ├── embeddings.py           # embed_text(), embed_batch() — model abstracted
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
# Swap LLM_MODEL string to change provider. Zero code changes needed.
LLM_MODEL=nvidia_nim/meta/llama-3.1-8b-instruct   # or: groq/llama3-8b-8192, openai/gpt-4o-mini
LLM_API_KEY=                     # LiteLLM reads this for all providers
LLM_API_BASE=                    # optional: required for NVIDIA NIM custom base URL
LLM_TIMEOUT_SECONDS=20           # per-call timeout, applied in core/llm/client.py
LLM_MAX_RETRIES=4                # max retry attempts before raising WandrLLMError

# Observability
LANGFUSE_PUBLIC_KEY=             # optional — NoOpTracer used if missing
LANGFUSE_SECRET_KEY=

# Geo
NOMINATIM_USER_AGENT=wandr-dev-yourname@email.com   # required by OSM policy

# OSRM
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
| `core/llm/client.py` | tenacity 4x, exponential wait 2–30s | per-call=`LLM_TIMEOUT_SECONDS` | read `Retry-After` header, sleep that duration before retry | raise `WandrLLMError(code="llm_unavailable")` |
| LangGraph graph (total) | no retry — nodes handle their own | `asyncio.wait_for(45s)` total | N/A | emit SSE `error` event, close stream cleanly |
| LangGraph iteration guard | N/A — hard ceiling | N/A | N/A | compile partial result, add `"max_iterations_reached"` warning, route to validation |
| `search/places_index.py` | no retry | N/A | N/A | return `[]` → planner uses PostGIS radius fallback |

**Retry only on:** `httpx.TimeoutException`, `httpx.ConnectError`, `litellm.Timeout`, `litellm.RateLimitError`
**Never retry on:** 404, 422, 400, or any client error — these are bugs, not transient failures.

---

## core/llm/client.py — Design
> **This is the only file in the entire codebase that imports litellm. No exceptions.**

```python
# src/core/llm/client.py
# Gateway + Strategy Pattern: swap LLM provider by changing LLM_MODEL env var only.
# All callers use chat_completion() — they never know which provider is active.

from litellm import acompletion, RateLimitError, Timeout as LLMTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio, httpx
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
        # Read Retry-After header if present, sleep before tenacity retries
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise  # re-raise so tenacity counts this as a retry
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e
```

**Usage in nodes:**
```python
# nodes/preference.py — correct
from src.core.llm.client import chat_completion
result = await chat_completion(messages=[...], response_format={"type": "json_object"})

# WRONG — never do this anywhere
from groq import Groq  # ❌
import litellm         # ❌ — use core/llm/client.py
```

---

## travel_engine — Design

The travel intelligence layer. All destination-agnostic planning rules live here.
LangGraph nodes call this layer — they do not contain planning logic themselves.
**No LLM calls. No external I/O. Pure Python only.**

### travel_rules.py
Constants and configuration that govern all planning decisions.
```python
MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30        # minimum gap between stops for transit
MAX_DAILY_TRAVEL_MIN = 180        # 3 hours travel per day maximum
VISIT_DURATION_BY_CATEGORY = {
    "monastery": 45,
    "viewpoint": 20,
    "museum": 60,
    "trek": 180,
    "park": 30,
    "cultural": 45,
}
CATEGORY_WEIGHTS = {
    "photography": 1.4,
    "offbeat": 1.3,
    "viewpoint": 1.2,
    "trek": 1.1,
    "cultural": 1.0,
    "family": 0.9,
}
MORNING_ONLY_CATEGORIES = ["viewpoint", "sunrise_point"]  # Tiger Hill = sunrise only
AVOID_SAME_DAY_PAIRS = [("monastery", "monastery")]       # don't stack same category
```

### place_selector.py
Answers: *which places? why these? what gets excluded?*
- Filter candidates by interest tags and budget
- Apply exclusion rules (e.g. a sunrise viewpoint cannot be Day 2 Stop 4 at 3pm)
- Score with category weights from travel_rules
- Remove places that conflict with each other on the same day
- `explain_selection(place, score_breakdown) → str` — logged to evaluation

### day_allocator.py
Answers: *how many places per day? how long at each?*
- Calculate realistic visit duration per category from `VISIT_DURATION_BY_CATEGORY`
- Cap day load by total time budget (8hr active day)
- Geographic pre-clustering: places within 10km radius seeded into same day candidate pool
- Distribute places across days by cluster and time load

### route_optimizer.py
Answers: *what order? how much travel time?*
- Nearest-neighbour ordering within each day's cluster
- OSRM travel times between consecutive stops (via `geo/osrm.py` — uses its own resilience contract)
- If total travel > `MAX_DAILY_TRAVEL_MIN` → drop lowest-scored stop and retry
- Output: ordered stops per day with realistic `travel_time_min` between each

### trip_validator.py
Answers: *is this a good, realistic trip?*
- Total daily travel time < `MAX_DAILY_TRAVEL_MIN`
- No place repeated across days
- Sunrise/morning-only places scheduled in morning slots (order ≤ 2)
- At least one "anchor" attraction per day (score > 0.7)
- Geographic coherence: std deviation of day's place coordinates < threshold

---

## evaluation — Design

Every generated trip is recorded. Not for users — for you, to improve quality over time.

### What gets stored (TripEvaluation)
```python
class TripEvaluation:
    id: UUID
    trip_id: UUID | None          # null if anonymous, linked if saved
    destination_id: UUID

    # Input
    raw_input: str
    parsed_preferences: dict      # what the preference node extracted

    # Pipeline
    candidates_retrieved: int     # how many POIs came back from Qdrant
    candidates_after_ranking: int # after scoring

    # Output
    final_route: dict             # the actual itinerary JSON
    places_per_day: list[int]     # [5, 6, 4] — distribution
    total_distance_km: float

    # Performance
    generation_time_ms: int
    token_usage: dict             # {preference_node: 120, itinerary_node: 890}
    llm_model: str                # from get_settings().LLM_MODEL — tracks which provider was used
    llm_retry_count: int          # how many retries the LLM needed this generation

    # Resilience signals
    used_geo_fallback: bool       # True if PostGIS was used instead of Qdrant
    used_osrm_fallback: bool      # True if haversine was used instead of OSRM
    abort_triggered: bool         # True if max_iterations was hit

    # Quality signals (filled later)
    validation_passed: bool
    validation_warnings: list[str]
    user_saved: bool              # did the user save this trip?
    user_edited: bool             # did they modify it? (strong quality signal)

    created_at: datetime
```

### Why this matters
- `user_saved=True` + `validation_passed=True` = good trip signal
- `user_edited=True` = something was wrong — which places got removed?
- High `generation_time_ms` = which node is slow?
- Low `candidates_retrieved` = Qdrant data gap for that destination
- `validation_warnings` patterns = systematic planner bugs
- High `llm_retry_count` = destination is hitting rate limits — candidate for pre-caching
- `abort_triggered=True` = LangGraph loop bug — investigate immediately
- `used_geo_fallback=True` consistently = Qdrant reliability issue

You will look at this data after 50 generated trips and know exactly what to fix.

---

## Phase Blueprint

### Legend
- 📦 Package installed at this step
- 🏗️ LLD pattern
- 🚨 Failure boundary
- ☁️ Production consideration
- 🔒 Resilience contract applied (see Resilience Contracts table)

---

### P0 — Scaffold, Config & Core Conventions
**2 days · 10 steps**

#### 0.1 Repo + full directory skeleton
- Create entire folder tree. Empty `__init__.py` in each folder.
- Includes `travel_engine/`, `evaluation/`, `core/llm/` from the start.
- Create `AGENT.md` at repo root (full content above). This is step one — before any code.
- 🏗️ **Modular Monolith** — each domain folder self-contained
- 🚨 Import failure at startup → clear module path in error, not silent 500
- ✅ `find src/ -type d | sort` → full tree, zero import errors. `cat AGENT.md` → guardrails visible.

#### 0.2 src/config.py — Pydantic Settings
- 📦 `pydantic-settings`
- `class Settings(BaseSettings)` — all env vars grouped by concern
- `@lru_cache def get_settings()` — loaded once per process
- Includes: `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TIMEOUT_SECONDS=20`, `LLM_MAX_RETRIES=4`
- 🏗️ **Singleton** — no re-parsing on every request
- ☁️ Dev reads `.env` file. Prod reads real env vars (Railway/Render/ECS). Zero code change.
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
- `chat_completion(messages, model=None, response_format=None) → str`
- Reads `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TIMEOUT_SECONDS` from `get_settings()`
- tenacity retry: `stop_after_attempt(LLM_MAX_RETRIES)`, `wait_exponential(min=2, max=30)`
- On `RateLimitError` (429): read `Retry-After` header, `asyncio.sleep(retry_after)`, then re-raise for tenacity
- On `Timeout`: re-raise for tenacity
- After all retries exhausted: raise `WandrLLMError(code="llm_unavailable")`
- Log every retry with: `model`, `attempt_number`, `wait_seconds`, `error_type`
- 🏗️ **Gateway Pattern** — single LLM entry point. Swap provider: change `LLM_MODEL` env var. Zero code changes.
- 🏗️ **Strategy Pattern** — `model` parameter allows per-call override (e.g. cheaper model for enrichment)
- 🚨 All LLM errors caught here. `WandrLLMError` propagates to the node, node populates `state.errors`. Never a 500.
- 🔒 Resilience contract: see table above
- ✅ `await chat_completion([{"role":"user","content":"ping"}])` → string response. Kill the network → raises `WandrLLMError` after retries, not an httpx error.

#### 0.7 core/pagination.py
- `PageParams`: page=1, size=20, max=100, computed offset
- `PaginatedResponse[T](BaseModel, Generic[T])`: items, total, page, size, pages, has_next, has_prev
- `paginate(result, total, params)` helper
- 🏗️ **Generic Repository** — every list endpoint is typed and consistent
- ✅ `PaginatedResponse(items=[], total=55, page=1, size=20, pages=3)` → `has_next=True`

#### 0.8 core/responses.py
- `ApiResponse[T]`: success, data, message
- `ErrorResponse`: success=False, code, message, details
- 🏗️ **Response Envelope** — frontend has one error handler, not many
- ✅ Both models serialise to clean JSON

#### 0.9 core/exceptions.py — WandrError hierarchy
- `WandrError(code, message, status_code, details)` base
- Subclasses: `NotFoundError(404)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ExternalServiceError(502)`, `WandrLLMError(503)`
- `WandrLLMError` — raised only by `core/llm/client.py`, caught only by LangGraph nodes
- 🏗️ **Exception Hierarchy** — single global handler catches all domain errors
- 🚨 Unhandled exceptions → full traceback logged server-side, generic `ErrorResponse` to client. No stack trace leakage.
- ✅ `raise WandrLLMError(code="llm_unavailable")` → caught → 503 `ErrorResponse`

#### 0.10 src/main.py — app factory + lifespan + /health
- 📦 `fastapi` `uvicorn[standard]`
- `create_app() → FastAPI` factory — enables test client injection
- Lifespan: startup → configure_logging, DB ping, Qdrant ping. Shutdown → close pool.
- `GET /api/v1/health` → `{"status":"ok","env":"development","version":"1.0.0"}`
- 🏗️ **App Factory** — decouples creation from execution
- ☁️ `/health` used as liveness probe by Railway/Render/ECS. Returns 503 if DB unreachable.
- 🚨 DB ping fails at startup → log critical + `exit(1)`. Visible crash > silent broken state.
- ✅ `uvicorn src.main:app` → `GET /api/v1/health` → 200 + structured log line

---

### P1 — Database Foundation + Auth
**3 days · 8 steps**

#### 1.1 core/database/base.py — declarative base + mixins
- 📦 `sqlalchemy[asyncio]` `asyncpg`
- `Base = DeclarativeBase()`
- `UUIDMixin`: `id = mapped_column(UUID, default=uuid4, primary_key=True)`
- `TimestampMixin`: created_at server_default, updated_at onupdate
- `SoftDeleteMixin`: deleted_at nullable — repos filter `deleted_at IS NULL` by default
- 🏗️ **Mixin Inheritance** — horizontal reuse, each mixin does one thing
- ✅ `from src.core.database.base import Base, TimestampMixin` → no error

#### 1.2 core/database/session.py — async engine + pool
- `create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)`
- `async_sessionmaker(expire_on_commit=False)`
- `async def get_db() → AsyncSession` — yields, closes in finally
- 🏗️ **Unit of Work** — one session per request, shared transaction context
- ☁️ `pool_pre_ping=True` recycles stale connections on hosted Postgres (Neon/Supabase idle drops)
- 🚨 Connection timeout → `ExternalServiceError` 502, not 500
- ✅ `scripts/test_db_conn.py` → "PostgreSQL 16.x connected, pool ok"

#### 1.3 Alembic init + migration 001: PostGIS
- 📦 `alembic` `geoalchemy2`
- Configure `env.py` for async engine + Base metadata import
- Migration 001: `CREATE EXTENSION IF NOT EXISTS postgis`
- ☁️ Run `alembic upgrade head` as deploy step — never inside app startup
- 🚨 Failed migration auto-rolls back. Bad migration never takes down running app.
- ✅ `alembic upgrade head` → "Running upgrade → 001_enable_postgis"

#### 1.4 All core models — migration 002
- `auth/models.py` — User: id, email, name, avatar_url, google_id, is_active
- `places/models.py` — Place: id, osm_id(unique), name, category, tags(JSONB), summary, location(Geometry POINT 4326), destination_id
- `trips/models.py` — Trip: id, user_id(nullable), session_id, destination_id, days, preferences(JSONB), status(enum)
- `trips/models.py` — TripPlace: id, trip_id, place_id, day_number, order_in_day, travel_time_min, polyline
- `evaluation/models.py` — TripEvaluation (full schema above, including `llm_retry_count`, `used_geo_fallback`, `abort_triggered`)
- Indexes: `Place.osm_id`, `Place.destination_id`, `Trip.session_id`, `Trip.user_id`
- 🏗️ **Domain Model** — each model lives in its domain module
- 🚨 Missing index on high-query columns = silent prod degradation. Add now.
- ✅ `alembic upgrade head` → all tables + indexes visible in `psql \dt \di`

#### 1.5 core/database/base_repository.py — generic repo base
- `class BaseRepository[M, ID]`
- Methods: `get_by_id()`, `create()`, `update()`, `soft_delete()`, `list_paginated(filters, params) → tuple[list[M], int]`
- `list_paginated` auto-applies `deleted_at IS NULL` from SoftDeleteMixin
- 🏗️ **Generic Repository** — domain repos extend this, get CRUD free
- 🏗️ **Specification Pattern** — `filters: dict` not raw SQL in callers
- ✅ `from src.core.database.base_repository import BaseRepository` → no error

#### 1.6 core/security/jwt.py + permissions.py
- 📦 `python-jose[cryptography]`
- `create_access_token(user_id, email) → str` — HS256, 7 day expiry
- `verify_token(token) → TokenPayload | None` — returns None on invalid, never raises
- `require_auth` → raises UnauthorizedError. `optional_auth` → returns user or None.
- ☁️ SECRET_KEY in prod = long random string from env, never hardcoded. Rotate by changing env var.
- 🚨 Expired token → 401. Malformed token → 401. Never 422 or 500.
- ✅ `verify_token(create_access_token(...))` → payload. `verify_token("bad")` → None

#### 1.7 auth/ — repository, service, router
- 📦 `httpx` (used for Google OAuth + all external HTTP going forward)
- `UserRepository(BaseRepository[User, UUID])`: `get_by_email()`, `get_by_google_id()`
- `AuthService`: `upsert_google_user()`, anonymous session UUID in httpOnly cookie
- `GET /api/v1/auth/google` → `GET /api/v1/auth/callback` → `GET /api/v1/auth/me` → `POST /api/v1/auth/logout`
- 🏗️ **Service Layer** — router calls service only, service calls repo, router knows nothing about DB
- 🚨 Google OAuth timeout → `ExternalServiceError` 502. Callback failure → redirect to `/auth/error`, never a 500 page.
- ✅ `GET /api/v1/auth/me` (no token) → `{"data":{"is_guest":true,"session_id":"uuid..."}}`

#### 1.8 core/middleware/logging.py
- Generate `X-Request-ID` per request, bind to structlog context
- Log `request.start` and `request.end` with latency_ms
- Return `X-Request-ID` in response headers
- 🏗️ **Chain of Responsibility** — middleware chain: request_id → logging → auth → rate_limit → handler
- ☁️ `X-Request-ID` in response lets support correlate user bug reports to specific log lines
- ✅ `GET /api/v1/health` → response header `X-Request-ID` present + `request.end` log with latency_ms

---

### P2 — Geo Foundation
**4 days · 7 steps**

#### 2.1 geo/geocoder.py — Nominatim client
- `geo/schemas.py`: `GeocodedPlace(name, lat, lng, osm_place_id, country, display_name)`
- `geocode(query) → GeocodedPlace | None` — async httpx, 1 req/sec rate limit, User-Agent from config
- httpx client: `connect_timeout=5s`, `read_timeout=10s`, `timeout=15s` (total)
- LRU cache on query string — same query never hits Nominatim twice in same process
- 🏗️ **Gateway Pattern** — all geocoding through one module. Swap provider by changing this file only. Callers use `geocode()` only — never import httpx or Nominatim URLs directly.
- ☁️ MVP: Nominatim free. Scale: add Redis cache layer here before calling Nominatim. Zero caller changes.
- 🚨 Nominatim timeout/connect fail → tenacity 3x retry, exponential 1–8s. After 3 failures → return None. Caller raises DestinationNotFound (404).
- 🔒 Resilience contract: see table above
- ✅ `scripts/test_geocoder.py "Darjeeling"` → `GeocodedPlace(lat=27.041, lng=88.263)`. Kill network → returns None after retries, no exception bubbles up.

#### 2.2 geo/overpass.py — POI scraper
- 📦 `tenacity` (already installed at 0.6 — confirm, do not reinstall)
- `RawPOI(osm_id, name, lat, lng, category, raw_tags: dict)`
- OverpassQL: `tourism=attraction|viewpoint|museum|monastery` + `leisure=park` + `highway=trailhead` within radius
- httpx client: `connect_timeout=10s`, `read_timeout=30s` (Overpass is legitimately slow on large queries)
- Filter: unnamed nodes discarded. Deduplicate by osm_id. Store all raw OSM tags.
- 🏗️ **Gateway Pattern** — single Overpass entry point. Caller never constructs OverpassQL directly.
- 🚨 Overpass timeout/connect fail → tenacity 3x retry, exponential 2–16s. After 3 failures → return `[]`. Seed script logs "Overpass unavailable, 0 POIs fetched" and continues. Never raises. Zero live app impact (script-only).
- 🔒 Resilience contract: see table above
- ✅ `scripts/test_overpass.py 27.041 88.263 30` → "Fetched 144 POIs". Kill network mid-run → "Overpass unavailable, 0 POIs" in logs, script exits 0.

#### 2.3 places/repository.py — upsert + radius + paginated
- `PlaceRepository(BaseRepository[Place, UUID])`
- `upsert_from_poi(poi, destination_id)` — `ON CONFLICT(osm_id) DO UPDATE`
- `find_within_radius(lat, lng, km)` — `ST_DWithin` on location column
- `list_by_destination(destination_id, params)` — inherits paginate from base
- 🚨 PostGIS extension missing → clear error at startup ping, not cryptic SQL error mid-request
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
- httpx client: `connect_timeout=5s`, `read_timeout=10s`
- ☁️ Public OSRM demo for MVP. Prod: self-hosted OSRM or Valhalla. Swap `OSRM_BASE_URL` in config only.
- 🚨 OSRM timeout → tenacity 2x retry, 1s fixed wait → if still fails, compute haversine straight-line × 1.4 factor, return as `RouteResult`. Log warning. Itinerary still valid. Never fails a user request.
- 🔒 Resilience contract: see table above
- ✅ `get_route([(27.04,88.26),(27.03,88.27)])` → `RouteResult(distance_km=1.8, polyline="...")`. Kill OSRM → returns straight-line result with log warning.

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
- 🚨 Invalid UUID in path → 422 from Pydantic. Missing destination_id → 422. Both use `ErrorResponse` shape.
- ✅ `GET /api/v1/places?destination_id=...&page=2&size=10` → `{"total":144,"page":2,"pages":15,"has_next":true}`

---

### P3 — Place Knowledge Layer
**3 days · 5 steps**

#### 3.1 search/client.py — Qdrant init
- 📦 `qdrant-client`
- `get_qdrant_client()` cached singleton
- `ensure_places_collection()` idempotent — vector size=384, cosine distance
- Called in app lifespan startup
- ☁️ Local: `QDRANT_URL=http://localhost:6333`, no key. Prod: `QDRANT_URL=https://xxx.qdrant.io` + `QDRANT_API_KEY`. Zero code change.
- 🚨 Qdrant unreachable at startup → log warning, set `search_available=False` flag. Planner falls back to PostGIS. App still serves requests.
- 🚨 Embedding model load failure at startup (`sentence-transformers` OOM or corrupt cache) → log critical + set `search_available=False`. Fall through to PostGIS same as Qdrant failure. Never `exit(1)` — app can still serve without semantic search.
- ✅ App startup → "Qdrant collection 'places' ready (0 vectors)" in logs

#### 3.2 search/embeddings.py — embed_text abstraction
- 📦 `sentence-transformers` — runs locally, no API key, free forever. Model: `all-MiniLM-L6-v2` (384d, 80MB)
- `embed_text(text: str) → list[float]` — model loaded once at module level inside try/except
- `embed_batch(texts: list[str]) → list[list[float]]`
- Model load wrapped in try/except: failure sets `_model = None`, `embed_text` returns empty list, `search_available=False` flag set
- 🏗️ **Strategy Pattern** — swap to OpenAI/Groq embeddings by changing one function body, not all callers
- ☁️ sentence-transformers runs in prod too (model cached after first download). No API cost.
- ✅ `embed_text("sunrise photography")` → list of 384 floats. Import with no GPU/large RAM → degrades gracefully.

#### 3.3 places/service.py — enrich_place()
- `enrich_place(place) → EnrichedPlace(summary, tags)`
- Calls `core/llm/client.py:chat_completion()` with JSON mode — never imports litellm directly
- LLM prompt: name + raw OSM tags → `{summary: str, tags: list[str]}`
- Tags from controlled vocab: `offbeat, photography, viewpoint, trek, monastery, cultural, family, nature, adventure`
- Skip if `place.summary` already set — re-runnable
- 🚨 `WandrLLMError` (after all retries in client.py) → log + skip place, continue batch. Batch never aborts for one failure.
- 🚨 Rate limit (429) handled inside `core/llm/client.py` — this caller does not need to handle it
- ✅ `enrich_place(tiger_hill)` → `{"summary":"Tiger Hill is...","tags":["photography","viewpoint","sunrise"]}`

#### 3.4 search/places_index.py — upsert + semantic search
- `upsert_place(place)` — embeds summary+tags, stores with payload: `{place_id, name, destination_id, lat, lng, tags, category}`
- `search_places(query, destination_id, top_k) → list[PlaceSearchResult]`
- `PlaceSearchResult`: place_id, name, score, lat, lng, tags
- 🏗️ **Repository Pattern** — Qdrant treated as another persistence layer
- 🚨 Qdrant search failure → catch, log warning, return empty list. Planner uses PostGIS fallback. Degraded but functional.
- ✅ `search_places("photography sunrise", darjeeling_id, 10)` → Tiger Hill first

#### 3.5 scripts/enrich_places.py + scripts/index_places.py
- `enrich_places.py --destination Darjeeling` — batches of 10, progress printed, re-runnable
- `index_places.py --destination Darjeeling` — embeds all enriched places, upserts to Qdrant
- ☁️ Run from local machine pointing at prod `DATABASE_URL` + `QDRANT_URL`. No CI/CD needed for data ops at MVP.
- ✅ Both scripts finish → "Indexed 144/144". Qdrant dashboard shows 144 vectors.

---

### P4 — Travel Engine (Intelligence Layer)
**4 days · 6 steps**

> This phase builds the destination-agnostic planning rules before the LangGraph nodes use them.
> Rules here. Logic here. Nodes are thin wrappers. **No LLM calls. No external I/O. Pure Python only.**

#### 4.1 travel_engine/travel_rules.py — constants + configuration
- All constants as listed in travel_engine design section above
- 🏗️ **Configuration Object** — rules are data, not logic. Editable without touching algorithms.
- ✅ `from src.travel_engine.travel_rules import MAX_PLACES_PER_DAY` → 6

#### 4.2 travel_engine/place_selector.py — which places? why? what's excluded?
- `select_places(candidates, preferences, destination) → list[ScoredPlace]`
- Apply `CATEGORY_WEIGHTS` to raw Qdrant scores
- Exclusion rules: morning-only places excluded if no morning slot available
- Budget filter: luxury places filtered out on budget preference
- Conflict filter: remove one of a same-day pair that violates `AVOID_SAME_DAY_PAIRS`
- `explain_selection(place, score_breakdown) → str` — why was this place chosen? (logged to evaluation)
- 🏗️ **Strategy Pattern** — selection criteria configurable, testable in isolation
- ✅ `select_places(36 candidates, {interests:["photography"]})` → photography places ranked higher, budget conflicts removed

#### 4.3 travel_engine/day_allocator.py — how many places per day?
- `allocate_days(selected_places, days, preferences) → list[list[ScoredPlace]]`
- Calculate time budget per day: `8hr - travel_buffer = available_visit_time`
- Assign places until day time budget exhausted or `MAX_PLACES_PER_DAY` reached
- Geographic pre-clustering: places within 10km radius seeded into same day candidate pool
- Output: `[[day1_candidates], [day2_candidates], ...]` — not yet ordered
- ✅ `allocate_days(18 places, 3)` → 3 lists, each ≤6 places, total visit time per day < 8hrs

#### 4.4 travel_engine/route_optimizer.py — what order? how much travel time?
- `optimize_route(day_places, origin_lat, origin_lng) → list[OrderedStop]`
- Greedy nearest-neighbour: start from place furthest from accommodation center, add nearest unvisited
- Fetch OSRM travel times via `geo/osrm.py` (resilience contract applied there — this caller gets clean result or haversine fallback)
- If total travel > `MAX_DAILY_TRAVEL_MIN` → drop lowest-scored stop and retry (max 3 drop attempts to prevent infinite loop)
- `OrderedStop`: place, order, travel_time_from_prev_min, arrival_note (e.g. "Start early — 45min drive")
- 🏗️ **Template Method** — optimize_route defines the algorithm skeleton, OSRM call is injectable
- 🚨 Drop-retry loop capped at 3 attempts. If still over budget after 3 drops, return best available and add warning.
- ✅ `optimize_route(day1_places)` → ordered stops with travel times, total travel < 180min

#### 4.5 travel_engine/trip_validator.py — is this a good trip?
- `validate_trip(itinerary) → ValidationResult(passed, warnings, errors)`
- Rules checked:
  - Total daily travel < `MAX_DAILY_TRAVEL_MIN`
  - No place repeated across days
  - Morning-only places in morning slots (order ≤ 2)
  - At least one "anchor" attraction per day (score > 0.7)
  - Geographic coherence: std deviation of day's place coordinates < threshold
- Returns warnings (non-blocking) and errors (blocking)
- 🏗️ **Chain of Responsibility** — each rule is a separate check function, easy to add/remove rules
- ✅ `validate_trip(good_itinerary)` → `errors=[], warnings=[]`. `validate_trip(bad_itinerary)` → specific error messages.

#### 4.6 Wire travel_engine into planner nodes — integration test
- `planner/graph/nodes/ranking.py` → calls `place_selector.select_places()`
- `planner/graph/nodes/route_planner.py` → calls `day_allocator.allocate_days()` + `route_optimizer.optimize_route()`
- `planner/graph/nodes/validation.py` → calls `trip_validator.validate_trip()`
- LangGraph nodes become thin: receive state, call travel_engine, update state, return
- ✅ `scripts/test_travel_engine.py` → "3-day Darjeeling trip: all rules passed, travel times realistic"

---

### P5 — AI Planner — LangGraph Agent
**5 days · 10 steps**

#### 5.1 planner/graph/state.py — TravelState TypedDict
- 📦 `langgraph`
- Input: `destination_id, destination_name, destination_lat, destination_lng, raw_input, session_id`
- Prefs: `days, budget, interests, include_offbeat, include_trekking`
- Working: `candidate_pois, ranked_pois, route (list[list[OrderedStop]])`
- Output: `itinerary (dict)`
- Meta: `errors (list[str]), warnings (list[str]), trace_id`
- **Resilience fields:**
  - `iteration_count: int` — incremented by `iteration_guard` before each node
  - `max_iterations: int = 5` — hard ceiling, set at graph entry, never modified
  - `abort_triggered: bool = False` — set True when ceiling hit
  - `llm_retry_count: int = 0` — incremented by nodes when `WandrLLMError` triggers fallback
  - `used_geo_fallback: bool = False` — set True by poi_retrieval node if PostGIS used
  - `used_osrm_fallback: bool = False` — set True by route_planner node if haversine used
- 🏗️ **State Machine** — explicit shared state, no hidden side effects between nodes, fully inspectable
- ✅ `s: TravelState = {}` → no type error

#### 5.2 planner/graph/builder.py — graph with iteration guard
- 📦 `langgraph` (already listed at 5.1)
- `StateGraph(TravelState)` with 7 nodes (adds `iteration_guard`)
- Edges: `START → iteration_guard → preference → iteration_guard → poi_retrieval → iteration_guard → ranking → iteration_guard → route_planner → iteration_guard → itinerary → validation → END`
- `iteration_guard` uses conditional edge: if `abort_triggered` → skip to `validation`. Else → continue.
- `build_graph() → CompiledGraph` — module-level singleton
- 🏗️ **Builder Pattern** — graph assembly separated from execution
- 🚨 Graph compilation error (wrong edge name) caught at startup, not first request
- ✅ `graph.invoke(minimal_state)` → all node names in logs in order, `iteration_count` increments visible

#### 5.3 planner/graph/nodes/iteration_guard.py — hard iteration ceiling
- Runs before every non-trivial node (wired via builder)
- Increments `state.iteration_count`
- If `state.iteration_count >= state.max_iterations`:
  - Sets `state.abort_triggered = True`
  - Adds `"max_iterations_reached"` to `state.warnings`
  - Compiles whatever is currently in `state.route` into a partial itinerary
  - Returns state — conditional edge in builder routes to `validation` node
- 🚨 This node never raises. It always returns a usable state.
- ✅ Inject `iteration_count=5, max_iterations=5` into state → `abort_triggered=True` after guard runs, validation still executes, evaluation still recorded

#### 5.4 nodes/preference.py — structured LLM parse
- Calls `core/llm/client.py:chat_completion()` with `response_format={"type":"json_object"}`
- Parse result: `{days, budget, interests, include_offbeat, include_trekking}`
- Validate: days 1–14, interests from controlled list only
- On `WandrLLMError`: populate `state.warnings`, use sensible defaults (3 days, mid budget, no filters). Increment `state.llm_retry_count`. Never blocks user.
- 🚨 LLM 429 handled inside `core/llm/client.py`. This node only catches `WandrLLMError`.
- ✅ `node({"raw_input":"3 days offbeat photography"})` → `state.days=3, state.interests=["photography","offbeat"]`. Kill LLM → defaults applied, `state.warnings` has entry.

#### 5.5 nodes/poi_retrieval.py — Qdrant + PostGIS fallback
- Build query: `" ".join(state.interests)`
- `top_k = state.days × 12`
- Fetch full Place rows from Postgres for returned IDs
- 🚨 Qdrant unavailable → catch → `PlaceRepository.find_within_radius()`. Set `state.used_geo_fallback = True`. Log "using geo fallback". No user impact.
- ✅ `node(state photography+offbeat 3 days)` → `state.candidate_pois` has 36 places

#### 5.6 nodes/ranking.py — calls place_selector
- Calls `travel_engine.place_selector.select_places(candidates, preferences, destination)`
- Stores result in `state.ranked_pois`
- Node is ~5 lines — all logic in travel_engine
- ✅ `node(36 candidates)` → 18 selected, photography spots at top

#### 5.7 nodes/route_planner.py — calls day_allocator + route_optimizer
- Calls `day_allocator.allocate_days()` → groups into days
- Calls `route_optimizer.optimize_route()` per day → ordered stops with travel times
- If `route_optimizer` used haversine fallback (OSRM was down), set `state.used_osrm_fallback = True`
- Stores result in `state.route`
- Node is ~10 lines — all logic in travel_engine
- ✅ `node(18 places 3 days)` → `state.route` = 3 lists, geographically grouped, ordered

#### 5.8 nodes/itinerary.py — LLM narrative + OSRM polylines
- Calls `core/llm/client.py:chat_completion()` — structure comes from `state.route`, not LLM
- LLM writes day title + narrative paragraph only
- OSRM called per day sequence via `geo/osrm.py` → `encoded_polyline` + `total_distance_km` attached
- `get_tracer().trace()` wraps LLM call
- Output per day: `{day, title, narrative, total_distance_km, polyline, places:[{name,lat,lng,order,travel_time_min}]}`
- 🚨 `WandrLLMError` (after all retries) → template narrative fallback. Increment `state.llm_retry_count`. OSRM fail → straight-line fallback (handled in geo/osrm.py). Never blocks output.
- ✅ Full itinerary dict with narrative, place list, polyline per day

#### 5.9 nodes/validation.py — calls trip_validator + records evaluation
- Calls `travel_engine.trip_validator.validate_trip(state.itinerary)`
- Calls `evaluation.service.record_generation(state, validation_result, timing)` — stores TripEvaluation row
  - Records `llm_retry_count`, `used_geo_fallback`, `used_osrm_fallback`, `abort_triggered` from state
- On validation errors → `state.errors` populated, itinerary flagged `needs_review`
- 🚨 Validation fail → return itinerary with warnings, never 500. Evaluation always recorded even on partial failure or `abort_triggered`.
- ✅ `node(valid)` → `errors=[]`. `node(injected bad place)` → `errors=["hallucinated_place"]`

#### 5.10 scripts/test_agent.py — full end-to-end
- Input: destination=Darjeeling, `raw_input="3 days offbeat photography budget"`
- Assert: `errors=[]`, day count=3, all places have lat/lng, validation passed, `abort_triggered=False`
- Print Langfuse trace URL if keys configured
- ✅ Complete 3-day itinerary JSON, "validation: passed", evaluation row written to DB, `iteration_count` in logs

---

### P6 — Planner API + Persistence
**3 days · 5 steps**

#### 6.1 trips/ — repository + service
- `TripRepository(BaseRepository[Trip, UUID])`: `list_by_user()`, `list_by_session()`, `get_with_places()`
- `TripService.save_from_state(state, user_id, session_id) → Trip`
- Anonymous trips claimable after login (session_id match)
- 🏗️ **Unit of Work** — Trip + TripPlace written in one transaction, rollback on partial failure
- 🚨 Partial TripPlace insert fail → full rollback. Trip row never exists without its places.
- ✅ Save itinerary → `trip_id` returned → `get_with_places` → all stops present

#### 6.2 planner/router.py — POST /generate streaming SSE
- `POST /api/v1/planner/generate` body: `PlanRequest(destination_id, raw_input, days)`
- `StreamingResponse` content-type `text/event-stream`
- SSE events: `preferences_done` → `pois_found(count)` → `route_ready` → `itinerary_done(data=json)`
- `optional_auth` — guests can plan, registered users get auto-save
- **SSE stream wrapped in `asyncio.wait_for(graph.invoke(state), timeout=45.0)`**
- 🚨 `asyncio.TimeoutError` → emit SSE `error` event `{"code":"generation_timeout"}`, close stream. Never hangs.
- 🚨 Any other agent error mid-stream → emit `error` SSE event with code + message, close stream cleanly.
- 🔒 Resilience contract: 45s hard ceiling on total graph execution
- ✅ `curl -N POST /api/v1/planner/generate` → events stream one by one, final `data=` is full JSON. Stall LLM at 46s → stream closes with error event.

#### 6.3 trips/router.py — CRUD + paginated list + GeoJSON
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` (require_auth)
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` (optional_auth + ownership)
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public — shareable link)
- `DELETE /api/v1/trips/{id}` → 204 (require_auth + ownership)
- 🚨 Accessing another user's trip → 403 (not 404 — don't confirm existence)
- ✅ `GET /api/v1/trips/{id}/geojson` → paste to geojson.io → route renders on map

#### 6.4 core/middleware/rate_limit.py + planner cache
- Rate limiter: 10 req/min per IP on `/planner/generate`. Returns 429 + `Retry-After` header.
- Planner cache key: `sha256(destination_id + sorted_interests + days + budget)` — 1hr TTL
- Dev: in-memory dict. Prod (REDIS_URL present): Redis SET.
- ☁️ Prod: `REDIS_URL=Upstash` free tier. LLM API calls drop dramatically for popular destinations.
- 🚨 Rate limiter error → fail open (allow request) + log warning. Cache unavailable → skip cache, run agent fresh.
- ✅ Same input twice → 2nd response instant, no agent log lines. 11th rapid request → 429.

#### 6.5 Backend ship checklist
- [ ] `GET /api/v1/destinations/search?q=Darjeeling` → geocoded result
- [ ] `GET /api/v1/places?destination_id=...&page=2` → `PaginatedResponse` with `has_next/has_prev`
- [ ] `POST /api/v1/planner/generate` → SSE stream, final event = full itinerary JSON
- [ ] `GET /api/v1/trips/{id}/geojson` → valid GeoJSON, renders on geojson.io
- [ ] All errors return `ErrorResponse`. All lists return `PaginatedResponse`.
- [ ] `evaluation` table has rows after each generation, including `llm_retry_count` and `abort_triggered`
- [ ] `travel_engine` rules pass for Darjeeling + Manali + Goa
- [ ] `pytest tests/ -v` → all green
- [ ] `docker compose up` from clean state → works
- [ ] No hardcoded values in any file — all from `get_settings()`
- [ ] No direct `litellm`, `groq`, or `openai` imports outside `core/llm/client.py`
- [ ] No direct `httpx` calls to Nominatim/Overpass/OSRM outside `src/geo/`
- [ ] Kill LLM mid-generation → stream closes with `error` event, no hanging request, evaluation recorded
- [ ] Change `LLM_MODEL` env var to `groq/llama3-8b-8192` → zero code changes needed, app works
- [ ] Set `DATABASE_URL`, `QDRANT_URL`, `REDIS_URL`, `LLM_API_KEY`, `LLM_MODEL`, `SECRET_KEY` in prod env → zero code changes needed

---

## LLD Pattern Reference

| Pattern | Where used |
|---------|-----------|
| Modular Monolith | Overall project structure |
| Singleton | `get_settings()`, `get_qdrant_client()`, `build_graph()` |
| App Factory | `create_app()` in main.py |
| Generic Repository | `BaseRepository[M, ID]` |
| Unit of Work | Session per request, Trip+TripPlace transaction |
| Specification Pattern | `filters: dict` in repo queries |
| Service Layer | Router → Service → Repository only |
| Gateway Pattern | `geo/geocoder.py`, `geo/overpass.py`, `geo/osrm.py`, `core/llm/client.py` |
| Cache-Aside | Destinations lookup, planner result cache |
| Strategy Pattern | `embed_text()`, `score_place()`, `place_selector`, `chat_completion()` model param |
| Null Object Pattern | `NoOpTracer` |
| Response Envelope | `ApiResponse[T]`, `PaginatedResponse[T]` |
| Exception Hierarchy | `WandrError` → domain exceptions + `WandrLLMError` |
| Chain of Responsibility | Middleware stack, `trip_validator` rules |
| State Machine | `TravelState` through LangGraph |
| Builder Pattern | `build_graph()` |
| Configuration Object | `travel_rules.py` |
| Template Method | `route_optimizer` with injectable OSRM call |

---

## Failure Boundary Summary

| Layer | Failure | Response |
|-------|---------|----------|
| DB connection | Timeout / unreachable | `ExternalServiceError` 502, pool_pre_ping recycles stale connections |
| DB migration | Failed migration | Auto-rollback, running app unaffected |
| Nominatim | Timeout / connect fail | tenacity 3x retry → return None → `DestinationNotFound` 404 |
| Overpass | Timeout / connect fail | tenacity 3x retry → return `[]` → seed script logs and continues |
| OSRM | Timeout | tenacity 2x retry → haversine × 1.4 fallback. Itinerary still valid. |
| Qdrant | Unreachable | `search_available=False`, PostGIS radius fallback. `state.used_geo_fallback=True`. |
| Embedding model load | OOM / corrupt cache | `search_available=False`, PostGIS fallback. App still starts. |
| LLM (any node) | Timeout | Handled in `core/llm/client.py`: tenacity 4x → `WandrLLMError` → node applies fallback |
| LLM (any node) | 429 Rate Limit | `core/llm/client.py` reads `Retry-After`, sleeps, retries. Never propagates 429 to user. |
| LLM (preference) | `WandrLLMError` after retries | Sensible defaults applied. `state.llm_retry_count` incremented. |
| LLM (itinerary) | `WandrLLMError` after retries | Template narrative fallback. `state.llm_retry_count` incremented. |
| LLM (enrichment) | `WandrLLMError` | Log + skip place, continue batch. Script never aborts. |
| LangGraph loop | `iteration_count >= max_iterations` | `abort_triggered=True`, partial result compiled, routes to validation |
| LangGraph total | Execution > 45s | `asyncio.TimeoutError` caught in router, SSE `error` event emitted, stream closed |
| Langfuse | Any error | Caught as warning. Never propagates to request. |
| JWT | Expired / malformed | 401 ErrorResponse. Never 422 or 500. |
| Auth callback | OAuth failure | Redirect to `/auth/error`. Never 500 page. |
| Rate limiter | Internal error | Fail open (allow request) + log warning |
| Redis cache | Unavailable | Skip cache, run agent fresh. Cache is acceleration not dependency. |
| Planner agent | Mid-stream error | Emit `error` SSE event, close stream cleanly. Never hangs. |
| Trip save | Partial insert | Full transaction rollback. Trip never exists without its places. |
| Validation | Rules fail | Return itinerary with `warnings`, never 500. Always record evaluation. |

---

## Package Install Order

Packages are installed at the step they are first needed. Never before.

| Step | Package | Reason |
|------|---------|--------|
| 0.2 | `pydantic-settings` | Settings class |
| 0.4 | `structlog` | Logging |
| 0.5 | `langfuse` | AI tracing |
| 0.6 | `litellm` `tenacity` | LLM abstraction + retry (tenacity used in geo too) |
| 0.10 | `fastapi` `uvicorn[standard]` | App server |
| 1.1 | `sqlalchemy[asyncio]` `asyncpg` | Async DB |
| 1.3 | `alembic` `geoalchemy2` | Migrations + PostGIS types |
| 1.6 | `python-jose[cryptography]` | JWT |
| 1.7 | `httpx` | External HTTP (OAuth + geo calls) |
| 3.1 | `qdrant-client` | Vector search |
| 3.2 | `sentence-transformers` | Embeddings |
| 5.1 | `langgraph` | Agent framework |
| 6.5 | `pytest` `pytest-asyncio` `pytest-mock` | Tests |

**Removed:** `groq`, `langchain-groq` — replaced by `litellm` at step 0.6 which covers all providers.
