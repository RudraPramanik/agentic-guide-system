# Wandr Backend — Low-Level Design Patterns & Principles

> Every design decision is named explicitly. Patterns are introduced at the step that needs them.
> Full pattern inventory also lives in [`docs/blueprint_final.md`](../blueprint_final.md#lld-pattern-reference).

## Guiding Principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | Packages at point of use | Nothing in `requirements.txt` until the step that needs it |
| 2 | LLD pattern named per step | Document the pattern when you introduce it |
| 3 | Failure boundary per step | Every external call has timeout, retry, and named fallback |
| 4 | Production abstracted from step 1 | Same code runs locally and in prod via env vars |
| 5 | Lightest viable package | No heavy deps without justification |
| 6 | Travel intelligence is first-class | `travel_engine/` is pure Python, separate from LangGraph |
| 7 | Evaluation from day one | Every generation and edit is recorded |
| 8 | LLM provider swappable | All LLM calls through `core/llm/client.py` only |
| 9 | Resilience mandatory | Explicit timeouts, tenacity retry, never raw 500 from externals |
| 10 | Controlled AI-assisted dev | `AGENT.md` guardrails govern all code |
| 11 | Structure from code, narrative from LLM | Geometry, order, times never from free-form LLM output |
| 12 | Tools are typed contracts | Pydantic schemas on every planner tool |
| 13 | Agent loops are bounded | `max_tool_calls`, phase gating, validate-before-finish |

## Layering Rules

```
Router  →  Service  →  Repository  →  Database
  │           │
  │           └── may call: travel_engine, planner/tools, geo, search, core/llm
  │
  └── returns ApiResponse[T] or PaginatedResponse[T] only
```

**Hard bans:**

- Router never touches DB directly
- No `litellm` / `openai` / `groq` imports outside `core/llm/client.py`
- No Nominatim / Overpass / OSRM calls outside `src/geo/`
- No planner side effects inline in LangGraph nodes — use `planner/tools/` or domain services
- No I/O inside `travel_engine/` — routing times injected via `RoutingProvider`

## Pattern Catalog

### Implemented (steps 0.1–1.2)

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Modular Monolith** | `src/` package layout | Single deployable unit, clear domain boundaries |
| **Configuration Object** | `src/config.py` | All env vars in one `Settings` class |
| **Singleton** | `get_settings()` | `@lru_cache` — parsed once per process |
| **Context Propagation** | `core/observability/logging.py` | `bind_contextvars()` flows `request_id` through all log lines without per-call passing |
| **Null Object** | `NoOpTracer` in `core/observability/tracing.py` | Callers use tracer unconditionally; no `if tracer:` branches |
| **Gateway** | `core/llm/client.py` | Only LLM entry point; LiteLLM + tenacity retry |
| **Strategy** | `chat_completion(model=...)`, `chat_with_tools()` | Provider/model swappable via env vars |
| **Response Envelope (lists)** | `PaginatedResponse[T]`, `paginate()` | Every list endpoint returns same pagination shape |
| **Response Envelope (single)** | `ApiResponse[T]`, `ErrorResponse` | Success/error JSON shape for all endpoints |
| **Exception Hierarchy** | `WandrError` tree in `core/exceptions.py` | Domain errors → `ErrorResponse` via global handler |
| **App Factory** | `create_app()` in `main.py` | Decouples app creation from uvicorn execution; test client injection |
| **Lifespan** | `@asynccontextmanager` in `main.py` | Startup: logging, DB ping (fail-fast), Qdrant ping (warn-only). Shutdown: flush tracer, dispose pool |
| **Global Exception Handlers** | `main.py` | `WandrError` → status from exception; `RequestValidationError` → 422; `Exception` → 500 (no stack leak) |
| **Mixin Inheritance** | `core/database/base.py` | Horizontal reuse: `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` composed per model |
| **Lazy Singleton (engine)** | `get_engine()` in `session.py` | Module-level `_engine`; created on first DB access; one pool per process |
| **Unit of Work** | `get_db()` in `session.py` | One `AsyncSession` per HTTP request; rollback on error; close in `finally` |

#### Step 0.4 — Logging design detail

```python
# App lifespan (once)
configure_logging()

# Middleware (per request)
structlog.contextvars.bind_contextvars(request_id=request_id)

# Any layer
log = get_logger()
log.info("place_ranked", place_id=pid, score=score)
# → request_id appears automatically in output
```

Renderer selection reads `get_settings().ENVIRONMENT`:

- `"production"` → `JSONRenderer` (machine-parseable, ships to log aggregators)
- anything else → `ConsoleRenderer(colors=True)` (human-readable local dev)

`configure_logging()` is idempotent and falls back to `ConsoleRenderer` if settings are not yet loadable.

#### Step 0.5 — Tracing design detail

```python
# App lifespan startup
tracer = get_tracer()  # Langfuse or NoOpTracer — never None

# Any layer — no isinstance checks needed
tracer.trace("planner_run", input=request_summary)
tracer.trace("llm_call").generation("chat", model=model).end()

# App lifespan shutdown
flush_tracer()
```

`get_tracer()` reads `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` from `get_settings()`:

- both non-empty → `Langfuse` client (init failures → `NoOpTracer` + warning log)
- either missing → `NoOpTracer`
- cached in module-level `_tracer` on first call

`flush_tracer()` catches all exceptions and logs warnings — never propagates to user requests.

#### Step 0.6 — LLM gateway design detail

Module: `src/core/llm/client.py` — **only file that imports `litellm`**.

```python
from src.core.llm.client import chat_completion, chat_with_tools

text = await chat_completion(messages, response_format=None)
result = await chat_with_tools(messages, tools, tool_choice="auto")
# result.tool_calls  OR  result.content
```

- `chat_completion()` — unstructured or JSON-mode text via `response_format`
- `chat_with_tools()` — returns `LLMToolResponse` with `tool_calls` or `content`
- Provider/model swappable via `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` env vars
- Tenacity retry on `litellm.Timeout` / `litellm.RateLimitError`: `LLM_MAX_RETRIES` attempts, exponential wait 2–30s
- Rate-limit: sleeps `Retry-After` (or 5s) before re-raise
- After retries exhausted → `WandrLLMError(code="llm_unavailable")` (never raw provider errors)
- Every retry logged via structlog: `model`, `attempt_number`, `error_type`, `wait_seconds`

Packages: `litellm==1.89.1`, `tenacity==9.1.4`

#### Step 0.7 — Pagination design detail

Module: `src/core/pagination.py` — pure schema/math, no DB logic.

```python
# Router
@router.get("/places")
async def list_places(params: PageParams = Depends()) -> PaginatedResponse[PlaceOut]:
    items, total = await service.list(params.offset, params.size)
    return paginate(items, total, params)
```

- `PageParams` — FastAPI dependency: `page` (≥1), `size` (1–100), computed `offset`
- `PaginatedResponse[T]` — callers pass only `items`, `total`, `page`, `size`; `pages`, `has_next`, `has_prev` auto-computed
- `paginate(items, total, params)` — convenience wrapper for services/repos

#### Step 0.8 — Response envelope design detail

Module: `src/core/responses.py` — schema only, no logic.

```python
# Success (single resource)
return ApiResponse(data=trip_out)

# Error (global exception handler — step 0.10)
return JSONResponse(
    status_code=exc.status_code,
    content=ErrorResponse(code=exc.code, message=exc.message, details=exc.details).model_dump(),
)
```

- `ApiResponse[T]` — `success=True`, `data`, optional `message`
- `ErrorResponse` — `success=False`, `code`, `message`, optional `details`
- Lists use `PaginatedResponse[T]` (step 0.7); singles use `ApiResponse[T]`

#### Step 0.9 — Exception hierarchy design detail

Module: `src/core/exceptions.py`

| Class | status | code | Raised by |
|-------|--------|------|-----------|
| `WandrError` | 500 | custom | Base — never raised directly |
| `NotFoundError` | 404 | `not_found` | Services/repos |
| `UnauthorizedError` | 401 | `unauthorized` | Auth middleware |
| `ForbiddenError` | 403 | `forbidden` | Auth/ownership checks |
| `ExternalServiceError` | 502 | `external_service_error` | Geo/search gateways |
| `WandrLLMError` | 503 | `llm_unavailable` | `core/llm/client.py` only |

All subclasses expose `status_code`, `code`, `message`, `details` — global handler maps these to `ErrorResponse`. `WandrLLMError` is caught in planner nodes, not routers.

#### Step 0.10 — App factory design detail

Module: `src/main.py` — **only FastAPI entry point**. `uvicorn src.main:app`.

```python
# Module level — uvicorn target
app = create_app()

# Lifespan startup (ordered)
configure_logging()
log.info("wandr.startup", env=..., version=...)
await ping_db()          # failure → log critical + SystemExit(1)
GET {QDRANT_URL}/healthz # failure → warning only, app continues

# Lifespan shutdown
flush_tracer()
log.info("wandr.shutdown")
await dispose_engine()
```

- `create_app()` → `FastAPI(title="Wandr API", version=APP_VERSION, lifespan=lifespan)`
- Global handlers: `WandrError`, `RequestValidationError` (422), `Exception` (500, `exc_info=True` server-side)
- `GET /api/v1/health` → `ApiResponse` with `status`, `env`, `version`; 503 `ErrorResponse` if DB ping fails at request time
- DB lifecycle via `core/database/session.py` — see step 1.2 below
- Qdrant startup check uses `httpx.AsyncClient` (import inside lifespan); 5s connect/read timeout
- No router includes yet; no `X-Request-ID` middleware (step 1.8)

**Local dev port mapping** (see `docker-compose.yml`):
- Postgres host `5433` → container `5432` (avoids local Postgres on 5432)
- Qdrant host `6335` → container `6333` (avoids other Qdrant on 6333)

Packages: `fastapi==0.137.1`, `uvicorn[standard]==0.49.0`, `sqlalchemy[asyncio]==2.0.51`, `asyncpg==0.31.0`

#### Step 1.1 — Declarative base + mixins design detail

Module: `src/core/database/base.py` — zero domain awareness.

```python
class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), ...)
```

| Mixin | Columns | Key rule |
|-------|---------|----------|
| `UUIDMixin` | `id` | Python `default=uuid.uuid4` — ID available before INSERT for same-transaction FKs |
| `TimestampMixin` | `created_at`, `updated_at` | `server_default=func.now()` — DB timezone, not app server |
| `SoftDeleteMixin` | `deleted_at` | Column only; repos filter `deleted_at IS NULL` |

- SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` only — no `Column()`, no `relationship()` here
- `Base` has no `__abstract__`; mixins are plain classes mixed into concrete models

#### Step 1.2 — Async session + pool design detail

Module: `src/core/database/session.py` — async only; no sync `Session` or `sessionmaker`.

```python
# Router dependency (step 1.2+)
async def endpoint(db: AsyncSession = Depends(get_db)):
    ...

# Script / smoke test
async with AsyncSessionLocal() as session:
    ...
```

| Function | Role |
|----------|------|
| `get_engine()` | Lazy singleton; `pool_pre_ping=True`, `pool_recycle=3600`, `expire_on_commit=False` via factory |
| `get_session_factory()` | Lazy `async_sessionmaker` bound to engine |
| `get_db()` | FastAPI generator — yield session, rollback on exception, close in `finally` |
| `AsyncSessionLocal()` | Back-compat callable for scripts |
| `ping_db()` | Startup/health `SELECT 1` |
| `dispose_engine()` | Shutdown — dispose pool, reset `_engine` and `_session_factory` |

`pool_pre_ping=True` is mandatory for hosted Postgres (Neon/Supabase idle drops). `expire_on_commit=False` is mandatory for async — without it, attribute access after commit triggers lazy-load errors.

Connection verification: `python scripts/test_db_conn.py` (requires `docker compose up -d`).

### Planned (upcoming steps)

| Pattern | Location | Step |
|---------|----------|------|
| **Generic Repository** | `BaseRepository[M, ID]` | 1.5 |
| **Cache-Aside** | Destinations, planner cache | P2+ |
| **Protocol / DI** | `travel_engine` routing injection | P4 |
| **Strategy** | `RoutingProvider` | P4 |
| **Tool Registry** | `planner/tools/registry.py` | P5 |
| **Phase-Gated Tool Loop** | `agent` ↔ `tool_executor` | P5 |
| **Bounded ReAct** | `tool_loop_count` ceiling | P5 |
| **Bookend Nodes** | `parse_preferences`, `write_narrative` outside loop | P5 |
| **State Machine** | `TravelState` through LangGraph | P5 |
| **Builder** | `build_graph()` | P5 |
| **Chain of Responsibility** | Middleware stack, validator rules | 0.10+, P4 |

## Resilience Contract (summary)

Every external call must have:

1. Explicit `connect_timeout` and `read_timeout` on httpx
2. Tenacity retry per the blueprint Resilience Contracts table
3. A named fallback — external failure never becomes a 500

See `AGENT.md` and blueprint for per-service timeout/retry values.

## Planner Agent Constraints

| Constraint | Mechanism |
|------------|-----------|
| Tool names | `TOOL_REGISTRY` only — agent never invents tools |
| Tool args | Validated against Pydantic input schema before execution |
| Execution path | `execute_tool(name, input, ctx)` — nodes never call impl directly |
| Phase gating | Agent binds only tools for `state.agent_phase` |
| Loop ceiling | `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force WRAP_UP |
| Finish gate | `finish_plan` blocked until `validate_itinerary` ok or `abort_triggered` |
| Narrative | `write_narrative` runs outside tool loop as fixed post-loop node |
| Generation timeout | SSE wrapped in `asyncio.wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)` |
| Replan bound | `replan_loop_count < PLANNER_MAX_REPLAN_ATTEMPTS` before replan path |

## Evaluation Rule

`evaluation/` records **every** generation and **every** edit — including partial failures. Never skip.

## Constants Placement

| What | Where |
|------|-------|
| Env vars / tunables | `src/config.py` |
| Travel domain rules | `src/travel_engine/travel_rules.py` |
| Tool names, phase maps | `src/planner/tools/registry.py` |

No magic strings, numbers, or URLs elsewhere.
