# Wandr — P0 Cursor Prompts
> One prompt per sub-step. Paste each prompt into Cursor Chat (Agent mode) **in order**.
> Do not start the next prompt until the current step's ✅ validation passes.

---

## How to use these prompts

1. Open Cursor with the `wandr-backend/` folder as the workspace root.
2. Switch to **Agent mode** in Cursor Chat.
3. Paste the prompt for the current step. Do not add extra instructions — the prompt is complete.
4. Run the listed validation command after Cursor finishes. Only proceed when it passes.
5. If Cursor deviates from the blueprint (adds packages not listed, skips a pattern, writes logic in the wrong layer), stop it and paste the correction note at the bottom of the relevant prompt.

---

## Step 0.1 — Repo + Full Directory Skeleton + AGENT.md

```
You are implementing the Wandr backend (production-grade AI travel planner).
Read AGENT.md at the repo root before doing anything — it contains hard rules that govern every line of code in this project.

TASK: Create the full directory skeleton and AGENT.md.

This is step 0.1 of the blueprint. Do NOT install any packages. Do NOT write any logic yet.

─── WHAT TO CREATE ───

1. Create AGENT.md at the repo root with this exact content:

---
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
- On `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force transition to WRAP_UP phase.
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
---

2. Create these files at the repo root (empty for now):
   - requirements.txt
   - .env.example
   - alembic.ini  (just a placeholder comment: # configured in step 1.3)

3. Create the full directory tree below. Every folder gets an empty `__init__.py`. Every .py file listed here is EMPTY (just a module docstring, nothing else). Do not write any logic yet.

src/
  __init__.py
  main.py
  config.py
  core/
    __init__.py
    pagination.py
    responses.py
    exceptions.py
    llm/
      __init__.py
      client.py
    database/
      __init__.py
      base.py
      session.py
      base_repository.py
    security/
      __init__.py
      jwt.py
      permissions.py
    middleware/
      __init__.py
      logging.py
      rate_limit.py
    observability/
      __init__.py
      logging.py
      tracing.py
  auth/
    __init__.py
    router.py
    schemas.py
    models.py
    repository.py
    service.py
    dependencies.py
    exceptions.py
  destinations/
    __init__.py
    router.py
    schemas.py
    models.py
    repository.py
    service.py
    readiness.py
  places/
    __init__.py
    router.py
    schemas.py
    models.py
    repository.py
    service.py
  trips/
    __init__.py
    router.py
    schemas.py
    models.py
    repository.py
    service.py
    exceptions.py
  planner/
    __init__.py
    router.py
    schemas.py
    service.py
    routing_provider.py
    tools/
      __init__.py
      registry.py
      schemas.py
      check_readiness.py
      search_places.py
      rank_places.py
      build_route.py
      build_schedule.py
      validate_itinerary.py
      finish_plan.py
      ask_clarification.py
      reoptimize_routes.py
      drop_weakest_stop.py
      expand_poi_search.py
      accept_partial.py
    graph/
      __init__.py
      state.py
      builder.py
      messages.py
      nodes/
        __init__.py
        parse_preferences.py
        agent.py
        tool_executor.py
        write_narrative.py
        record_evaluation.py
  travel_engine/
    __init__.py
    travel_rules.py
    protocols.py
    place_selector.py
    day_allocator.py
    route_optimizer.py
    schedule_builder.py
    trip_validator.py
  evaluation/
    __init__.py
    models.py
    repository.py
    service.py
    schemas.py
  geo/
    __init__.py
    geocoder.py
    overpass.py
    osrm.py
    schemas.py
  search/
    __init__.py
    client.py
    embeddings.py
    places_index.py

scripts/
  seed_destination.py
  enrich_places.py
  index_places.py
  test_travel_engine.py
  test_agent.py

tests/
  __init__.py
  conftest.py
  auth/
    __init__.py
  planner/
    __init__.py
  geo/
    __init__.py
  trips/
    __init__.py
  destinations/
    __init__.py

alembic/
  __init__.py
  env.py  (placeholder comment only)
  versions/  (empty folder)

─── RULES FOR THIS STEP ───
- No package installs.
- No logic in any .py file — only a module docstring like: """Wandr — module name. Implemented in step X.Y."""
- Do not create any file not listed above.

─── VALIDATION ───
After creating everything, run:
  find src/ -type d | sort
  cat AGENT.md

Expected: full directory tree printed, AGENT.md content visible.
```

---

## Step 0.2 — src/config.py — Pydantic Settings

```
Read AGENT.md before proceeding.

TASK: Implement src/config.py — the single source of truth for all environment variables.

This is step 0.2. Install pydantic-settings now (first and only package this step).

─── INSTALL ───
Add to requirements.txt:
  pydantic-settings==2.3.0  # centralized env var parsing — step 0.2

Then install: pip install pydantic-settings==2.3.0

─── IMPLEMENT src/config.py ───

Requirements:
- One `Settings(BaseSettings)` class with ALL env vars for the entire project, grouped by concern.
- `@lru_cache` singleton `get_settings()` function — loaded once per process, never re-parsed.
- All fields typed. Required fields have no default (missing → ValidationError at startup).
- Optional fields have sensible defaults.

Include these fields exactly (names must match exactly — referenced across the codebase):

# Core
ENVIRONMENT: str = "development"   # "development" | "production"
DEBUG: bool = True
SECRET_KEY: str                    # required, no default

# Database
DATABASE_URL: str                  # required

# Vector search
QDRANT_URL: str = "http://localhost:6333"
QDRANT_API_KEY: str = ""           # empty for local

# Cache
REDIS_URL: str = ""                # empty = in-memory fallback

# LLM
LLM_MODEL: str = "nvidia_nim/meta/llama-3.1-8b-instruct"
LLM_API_KEY: str                   # required
LLM_API_BASE: str = ""             # optional, for custom base URLs
LLM_TIMEOUT_SECONDS: int = 20
LLM_MAX_RETRIES: int = 4

# Planner agent bounds
PLANNER_MAX_TOOL_CALLS: int = 12
PLANNER_MAX_REPLAN_ATTEMPTS: int = 2
PLANNER_GENERATION_TIMEOUT_SECONDS: int = 45
PLANNER_MIN_READINESS_SCORE: float = 0.3
PLANNER_AGENT_PHASE_STUCK_LIMIT: int = 3

# Observability
LANGFUSE_PUBLIC_KEY: str = ""      # optional
LANGFUSE_SECRET_KEY: str = ""      # optional

# Geo
NOMINATIM_USER_AGENT: str          # required — OSM policy
OSRM_BASE_URL: str = "https://router.project-osrm.org"

Use `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`.

─── IMPLEMENT .env.example ───
Create .env.example with all keys listed (values as placeholders), grouped with comments matching the Settings groups above. This is the dev onboarding reference.

─── RULES ───
- NEVER call `os.environ.get()` anywhere. This file is the only env access point.
- `get_settings()` must be decorated with `@lru_cache` from functools.
- No business logic in this file — only settings.

─── VALIDATION ───
Run:
  python -c "from src.config import get_settings; print(get_settings().LLM_MODEL)"

Expected: prints the LLM_MODEL default string without error.
(You will need a minimal .env with SECRET_KEY, DATABASE_URL, LLM_API_KEY, NOMINATIM_USER_AGENT set to any placeholder values for this test.)
```

---

## Step 0.3 — docker-compose.yml

```
Read AGENT.md before proceeding.

TASK: Create docker-compose.yml for local dev infrastructure only.

This is step 0.3. No package installs. No code changes.

─── IMPLEMENT docker-compose.yml ───

Services to define:

1. postgres:
   - Image: postgis/postgis:16-3.4
   - Container name: wandr_postgres
   - Environment: POSTGRES_USER=wandr, POSTGRES_PASSWORD=wandr, POSTGRES_DB=wandr
   - Ports: 5432:5432
   - Named volume: wandr_postgres_data → /var/lib/postgresql/data
   - Healthcheck: pg_isready -U wandr -d wandr, interval 5s, timeout 5s, retries 5

2. qdrant:
   - Image: qdrant/qdrant:latest
   - Container name: wandr_qdrant
   - Ports: 6333:6333, 6334:6334
   - Named volume: wandr_qdrant_data → /qdrant/storage

Define both named volumes at the bottom of the file.

─── RULES ───
- No Redis service — REDIS_URL is empty in dev (feature-flagged off).
- This file is used for LOCAL DEV ONLY. Production uses hosted services via env vars. Add a comment at the top: "# Local dev only. Never used in production."
- Do not add any application service (no wandr-api container here).

─── VALIDATION ───
Run:
  docker compose up -d
  docker compose ps

Expected: both containers show as "healthy" or "running".
```

---

## Step 0.4 — core/observability/logging.py — structlog

```
Read AGENT.md before proceeding.

TASK: Implement structured logging via structlog.

This is step 0.4. Install structlog now.

─── INSTALL ───
Add to requirements.txt:
  structlog==24.2.0  # structured logging — step 0.4

Then install: pip install structlog==24.2.0

─── IMPLEMENT src/core/observability/logging.py ───

Requirements:
- `configure_logging()` — call once at app startup (in lifespan). Idempotent if called twice.
- Environment-aware renderer:
  - ENVIRONMENT == "development" → `structlog.dev.ConsoleRenderer(colors=True)`
  - ENVIRONMENT == "production" → `structlog.processors.JSONRenderer()`
- Processing chain (in order):
  1. `structlog.contextvars.merge_contextvars` — pulls in bound context vars (request_id flows here)
  2. `structlog.processors.add_log_level`
  3. `structlog.processors.TimeStamper(fmt="iso")`
  4. The environment renderer
- Use `structlog.configure()` with these processors and `wrapper_class=structlog.BoundLogger`.
- Export `get_logger` as a convenience alias: `get_logger = structlog.get_logger`

Key design: `bind_contextvars(request_id=...)` called in middleware will automatically appear in every log line for that request. Callers never need to pass request_id manually.

─── RULES ───
- Read ENVIRONMENT from `get_settings()`. Never hardcode "development" as a string check outside config.
- `configure_logging()` must be safe to call before `get_settings()` has the full .env loaded — use a try/except with a default of ConsoleRenderer as fallback.
- Do not add any other processors not listed above.

─── VALIDATION ───
Run:
  python -c "
from src.core.observability.logging import configure_logging, get_logger
configure_logging()
log = get_logger()
log.info('boot', env='dev', step='0.4')
"

Expected: a formatted log line printed to stdout with the boot message and fields. No crash.
```

---

## Step 0.5 — core/observability/tracing.py — Langfuse

```
Read AGENT.md before proceeding.

TASK: Implement Langfuse tracing with a NoOpTracer fallback using the Null Object Pattern.

This is step 0.5. Install langfuse now.

─── INSTALL ───
Add to requirements.txt:
  langfuse==2.36.1  # LLM observability tracing — step 0.5

Then install: pip install langfuse==2.36.1

─── IMPLEMENT src/core/observability/tracing.py ───

Requirements:

1. `NoOpTracer` class — has an identical interface to the parts of Langfuse we use, but does nothing.
   Methods it must implement (all no-ops, return self or None):
   - `trace(name, **kwargs) → self`
   - `span(name, **kwargs) → self`
   - `generation(name, **kwargs) → self`
   - `update(**kwargs) → self`
   - `end(**kwargs) → self`
   - `flush() → None`

2. `get_tracer() → Langfuse | NoOpTracer`:
   - Read `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` from `get_settings()`.
   - If BOTH keys are non-empty strings: initialize and return a `Langfuse` client.
   - Otherwise: return `NoOpTracer()`.
   - Wrap Langfuse init in try/except — if it fails, log a warning via structlog and return `NoOpTracer()`.
   - Cache the result (module-level variable set on first call — not `@lru_cache` since Langfuse client isn't hashable).

3. `flush_tracer() → None` — calls `get_tracer().flush()`. Used in app shutdown lifespan.

─── RULES ───
- Callers NEVER write `if tracer:` or `if isinstance(tracer, Langfuse):`. The NoOpTracer makes this unnecessary — this is the Null Object Pattern.
- Langfuse errors (flush failures, network timeouts) must NEVER propagate to user requests. Catch them here, log as warnings only.
- Do not import Langfuse at module level in a way that crashes if the package isn't installed. Guard with try/except ImportError if needed.

─── VALIDATION ───
Run:
  python -c "
from src.core.observability.tracing import get_tracer, flush_tracer
tracer = get_tracer()
tracer.trace('test_trace', input='hello')
flush_tracer()
print('tracer type:', type(tracer).__name__)
"

Expected: no crash. Prints tracer type (either Langfuse or NoOpTracer depending on whether keys are set in .env). Both must work without error.
```

---

## Step 0.6 — core/llm/client.py — LiteLLM Abstraction

```
Read AGENT.md before proceeding.

TASK: Implement the LLM gateway — the ONLY file in the entire codebase that imports litellm.

This is step 0.6. Install litellm and tenacity now.

─── INSTALL ───
Add to requirements.txt:
  litellm==1.40.10   # LLM provider abstraction — step 0.6
  tenacity==8.3.0    # retry logic for all external calls — step 0.6

Then install: pip install litellm==1.40.10 tenacity==8.3.0

─── IMPLEMENT src/core/llm/client.py ───

This file has two public async functions. Implement both completely.

--- FUNCTION 1: chat_completion ---

Signature:
  async def chat_completion(
      messages: list[dict],
      model: str | None = None,
      response_format: dict | None = None,
  ) -> str:

Behavior:
- Calls `litellm.acompletion()` with:
  - model: `model or get_settings().LLM_MODEL`
  - messages: as passed
  - response_format: as passed (None = unstructured text)
  - api_key: `get_settings().LLM_API_KEY`
  - api_base: `get_settings().LLM_API_BASE or None`
  - timeout: `get_settings().LLM_TIMEOUT_SECONDS`
- Returns `response.choices[0].message.content` as a plain string.

Retry (tenacity decorator on this function):
- `stop_after_attempt(get_settings().LLM_MAX_RETRIES)` — use a callable that reads settings at retry time, not at import time.
- `wait_exponential(multiplier=1, min=2, max=30)`
- `retry_if_exception_type((litellm.Timeout, litellm.RateLimitError))`
- `reraise=False` — after all retries exhausted, raise WandrLLMError instead

On RateLimitError (inside the function, before re-raising):
- Read `Retry-After` header from the exception if present: `getattr(e, "retry_after", None) or 5`
- `await asyncio.sleep(float(retry_after))`
- Then re-raise so tenacity counts the attempt

After all retries exhausted:
- Raise `WandrLLMError(code="llm_unavailable", message=f"LLM call failed after retries: {type(e).__name__}")`

Log every retry attempt via structlog with fields: `model`, `attempt_number`, `error_type`, `wait_seconds`.

--- FUNCTION 2: chat_with_tools ---

Signature:
  async def chat_with_tools(
      messages: list[dict],
      tools: list[dict],
      tool_choice: str = "auto",
      model: str | None = None,
  ) -> "LLMToolResponse":

Where LLMToolResponse is a dataclass defined in this file:
  @dataclass
  class LLMToolResponse:
      tool_calls: list[dict]   # list of {name: str, arguments_json: str}
      content: str | None      # set if model responded without tool calls

Behavior:
- Same retry contract as chat_completion (same decorator, same error handling).
- Calls `litellm.acompletion()` with additionally: `tools=tools`, `tool_choice=tool_choice`
- Parse response:
  - If `response.choices[0].message.tool_calls` is non-empty:
    - Build `tool_calls` list: [{name: tc.function.name, arguments_json: tc.function.arguments}]
    - Return `LLMToolResponse(tool_calls=tool_calls, content=None)`
  - Else (model returned text without a tool call):
    - Return `LLMToolResponse(tool_calls=[], content=response.choices[0].message.content)`
- On any exception after retries: raise `WandrLLMError` same as chat_completion.

--- RULES (hard) ---
- This is the ONLY file that imports litellm. The word "litellm" must not appear in any other file.
- WandrLLMError is imported from `src.core.exceptions` — do not define it here.
- get_settings() is called inside the function body, not at module level — so settings are fresh per call.
- The tenacity `stop` argument must read `LLM_MAX_RETRIES` at retry time. Use a lambda or `before_sleep` hook, not a module-level constant.

─── VALIDATION ───
Run (requires valid LLM_API_KEY in .env):
  python -c "
import asyncio
from src.core.llm.client import chat_completion
result = asyncio.run(chat_completion([{'role':'user','content':'Reply with the single word: pong'}]))
print('Response:', result)
"

Expected: prints "Response: pong" (or similar single-word reply). No import errors.

Also verify the import guard:
  grep -r "import litellm" src/ --include="*.py" | grep -v "core/llm/client.py"

Expected: zero results — litellm imported nowhere else.
```

---

## Step 0.7 — core/pagination.py

```
Read AGENT.md before proceeding.

TASK: Implement the shared pagination models used by every list endpoint in the project.

This is step 0.7. No new package installs.

─── IMPLEMENT src/core/pagination.py ───

Implement all three of these in one file:

1. PageParams — FastAPI dependency for incoming pagination query params:
   - `page: int = 1` (minimum 1)
   - `size: int = 20` (minimum 1, maximum 100)
   - `offset` property: `(self.page - 1) * self.size`
   - Use `Query(ge=1)` and `Query(ge=1, le=100)` validators.

2. PaginatedResponse[T] — generic response model for all list endpoints:
   - `items: list[T]`
   - `total: int`         — total records in DB (not just this page)
   - `page: int`
   - `size: int`
   - `pages: int`         — computed: ceil(total / size), minimum 1
   - `has_next: bool`     — computed: page < pages
   - `has_prev: bool`     — computed: page > 1
   - Inherit from `BaseModel` and use `Generic[T]`.
   - All computed fields must be auto-calculated — callers only pass `items`, `total`, `page`, `size`.

3. paginate() helper function:
   - Signature: `def paginate(items: list[T], total: int, params: PageParams) -> PaginatedResponse[T]`
   - Constructs and returns PaginatedResponse from the three inputs.

─── RULES ───
- PageParams must work as a FastAPI dependency (passed via `Depends(PageParams)` in routers).
- PaginatedResponse must be fully generic — `PaginatedResponse[PlaceOut]`, `PaginatedResponse[TripOut]` etc. must all work.
- No database logic here — this is pure schema/math.

─── VALIDATION ───
Run:
  python -c "
from src.core.pagination import PaginatedResponse, PageParams, paginate

# Test computed fields
r = PaginatedResponse(items=[], total=55, page=1, size=20, pages=3, has_next=True, has_prev=False)
print('has_next:', r.has_next)   # True
print('pages:', r.pages)         # 3

# Test paginate helper
from dataclasses import dataclass
params = type('P', (), {'page': 2, 'size': 10, 'offset': 10})()
result = paginate(['a','b','c'], total=55, params=params)
print('result.has_next:', result.has_next)   # True
print('result.has_prev:', result.has_prev)   # True
print('result.pages:', result.pages)         # 6
"

Expected: all printed values match the comments above with no errors.
```

---

## Step 0.8 — core/responses.py

```
Read AGENT.md before proceeding.

TASK: Implement the two standard response envelope models used by every endpoint.

This is step 0.8. No new package installs.

─── IMPLEMENT src/core/responses.py ───

Implement both models in one file:

1. ApiResponse[T] — used by all single-resource endpoints:
   - `success: bool = True`
   - `data: T`
   - `message: str | None = None`
   - Inherit from `BaseModel` and `Generic[T]`.

2. ErrorResponse — used by the global exception handler:
   - `success: bool = False`
   - `code: str`        — machine-readable error code (e.g. "not_found", "llm_unavailable")
   - `message: str`     — human-readable message
   - `details: dict | None = None`  — optional structured detail (validation errors etc.)

─── RULES ───
- Both must inherit from `pydantic.BaseModel`.
- `ApiResponse[T]` must be fully generic — `ApiResponse[UserOut]`, `ApiResponse[TripOut]` etc. must all work.
- No logic here — only schema definitions.

─── VALIDATION ───
Run:
  python -c "
from src.core.responses import ApiResponse, ErrorResponse
import json

ok = ApiResponse(data={'id': '123', 'name': 'Darjeeling'})
print('ok:', json.dumps(ok.model_dump(), indent=2))

err = ErrorResponse(code='not_found', message='Destination not found', details={'destination_id': 'abc'})
print('err:', json.dumps(err.model_dump(), indent=2))
print('success fields match:', ok.success == True, err.success == False)
"

Expected: both print valid JSON. `ok.success` is True, `err.success` is False. No errors.
```

---

## Step 0.9 — core/exceptions.py — WandrError Hierarchy

```
Read AGENT.md before proceeding.

TASK: Implement the full exception hierarchy for the Wandr application.

This is step 0.9. No new package installs.

─── IMPLEMENT src/core/exceptions.py ───

Implement all exceptions in one file:

1. WandrError (base class):
   - Inherits from `Exception`.
   - Constructor: `__init__(self, code: str, message: str, status_code: int = 500, details: dict | None = None)`
   - Stores all four as instance attributes.

2. Domain exception subclasses (all inherit from WandrError):

   NotFoundError:
   - Default status_code=404
   - Default code="not_found"
   - Constructor: `__init__(self, message: str = "Resource not found", details: dict | None = None)`

   UnauthorizedError:
   - Default status_code=401, code="unauthorized"
   - Constructor: `__init__(self, message: str = "Authentication required")`

   ForbiddenError:
   - Default status_code=403, code="forbidden"
   - Constructor: `__init__(self, message: str = "Access denied")`

   ExternalServiceError:
   - Default status_code=502, code="external_service_error"
   - Constructor: `__init__(self, service: str, message: str, details: dict | None = None)`
   - Include `service` in `details` automatically: `{"service": service, **(details or {})}`

   WandrLLMError:
   - Default status_code=503, code="llm_unavailable"
   - Constructor: `__init__(self, code: str = "llm_unavailable", message: str = "LLM service unavailable", details: dict | None = None)`
   - This is the ONLY exception raised by `core/llm/client.py`.
   - It is caught ONLY in planner tool/node code — never in routers.

─── RULES ───
- WandrLLMError is the only exception imported by `core/llm/client.py`. All others are for domain use.
- All subclasses must preserve the `status_code`, `code`, `message`, `details` interface from WandrError — the global exception handler will use these to build `ErrorResponse`.
- Do not add a global exception handler here — that goes in main.py (step 0.10).

─── VALIDATION ───
Run:
  python -c "
from src.core.exceptions import (
    WandrError, NotFoundError, UnauthorizedError,
    ForbiddenError, ExternalServiceError, WandrLLMError
)

e1 = NotFoundError('Destination not found', details={'id': 'abc'})
print(e1.status_code, e1.code, e1.message)   # 404 not_found Destination not found

e2 = WandrLLMError(code='llm_unavailable', message='LLM timed out after retries')
print(e2.status_code, e2.code)               # 503 llm_unavailable

e3 = ExternalServiceError(service='nominatim', message='Geocode failed')
print(e3.status_code, e3.details)            # 502 {'service': 'nominatim'}

# Hierarchy check
print(isinstance(e1, WandrError))  # True
print(isinstance(e2, WandrError))  # True
"

Expected: all printed values match comments above. No errors.
```

---

## Step 0.10 — src/main.py — App Factory + Lifespan + /health

```
Read AGENT.md before proceeding.

TASK: Implement the FastAPI app factory, lifespan handler, global exception handler, and /health endpoint.
This is the final step of P0. It wires together everything built in steps 0.1–0.9.

─── INSTALL ───
Add to requirements.txt:
  fastapi==0.111.1       # web framework — step 0.10
  uvicorn[standard]==0.30.1  # ASGI server — step 0.10

Then install: pip install fastapi==0.111.1 "uvicorn[standard]==0.30.1"

─── IMPLEMENT src/main.py ───

Structure: App Factory pattern — `create_app()` returns the FastAPI instance.
`uvicorn` runs `src.main:app` where `app = create_app()` at module level.

1. Lifespan context manager (use `@asynccontextmanager`):
   Startup sequence (in order):
   a. Call `configure_logging()` from `core.observability.logging`
   b. Log "wandr.startup" with env and version
   c. Ping the database: run `SELECT 1` via the async engine. On failure: log critical "DB unreachable" + raise SystemExit(1) — crash loudly, not silently.
   d. Ping Qdrant: make an HTTP GET to `{QDRANT_URL}/healthz` via httpx with 5s timeout. On failure: log warning "Qdrant unreachable — search degraded" but DO NOT crash (Qdrant unavailable is recoverable).
   
   Shutdown sequence:
   e. Call `flush_tracer()` from `core.observability.tracing`
   f. Log "wandr.shutdown"
   g. Dispose the async engine connection pool.

2. create_app() factory:
   - Create `FastAPI(title="Wandr API", version="1.0.0", lifespan=lifespan)`
   - Register the global exception handler for WandrError (see below).
   - Register the global exception handler for RequestValidationError → 422 with ErrorResponse shape.
   - Register the global exception handler for unhandled Exception → log full traceback + return 500 ErrorResponse (never leak stack trace to client).
   - Return the app instance.

3. Global exception handler for WandrError:
   - Extract: status_code, code, message, details from the exception.
   - Return `JSONResponse(status_code=e.status_code, content=ErrorResponse(...).model_dump())`

4. GET /api/v1/health endpoint:
   - No auth required.
   - Returns: `{"status": "ok", "env": settings.ENVIRONMENT, "version": "1.0.0"}`
   - Use `ApiResponse` wrapper: `ApiResponse(data={"status":"ok","env":...,"version":"..."})`
   - If DB ping fails at request time: return 503 with `ErrorResponse(code="db_unavailable", message="Database unreachable")`

5. At module bottom: `app = create_app()`

─── RULES ───
- DB ping failure at startup = `SystemExit(1)`. Visible crash is better than zombie process.
- Qdrant ping failure at startup = warning log only. App continues. Search degrades gracefully.
- The global unhandled exception handler logs `exc_info=True` (full traceback server-side) but returns only a generic message to the client.
- No router includes yet — those come in later phases. Only `/api/v1/health` is registered here.
- For the Qdrant healthcheck httpx call: use `httpx.AsyncClient` with a 5s timeout. Do not import httpx at module level — import inside the lifespan function so it's clear it's a startup-only use.

─── VALIDATION ───
Run the app:
  uvicorn src.main:app --reload

In another terminal:
  curl -s http://localhost:8000/api/v1/health | python -m json.tool

Expected output:
  {
    "success": true,
    "data": {
      "status": "ok",
      "env": "development",
      "version": "1.0.0"
    },
    "message": null
  }

Also check the startup logs — you should see:
  - "wandr.startup" log line
  - DB ping success or crash with clear error
  - Qdrant ping result (warning if not running, no crash)

Also verify the X-Request-ID header is NOT yet present (that comes in step 1.8) — this confirms you haven't jumped ahead.
```

---

## P0 Complete — Verification Checklist

Before moving to P1, confirm every item below passes:

```bash
# 1. Full directory tree exists
find src/ -type d | sort

# 2. AGENT.md is at repo root and readable
cat AGENT.md | head -5

# 3. Settings loads without error
python -c "from src.config import get_settings; s = get_settings(); print(s.PLANNER_MAX_TOOL_CALLS)"
# Expected: 12

# 4. Structlog works
python -c "from src.core.observability.logging import configure_logging, get_logger; configure_logging(); get_logger().info('check', step='p0')"

# 5. Tracer works (no crash either way)
python -c "from src.core.observability.tracing import get_tracer; t = get_tracer(); t.trace('p0_check'); print(type(t).__name__)"

# 6. LLM client imports cleanly
python -c "from src.core.llm.client import chat_completion, chat_with_tools; print('LLM client OK')"

# 7. litellm not imported outside client.py
grep -r "import litellm" src/ --include="*.py" | grep -v "core/llm/client.py"
# Expected: zero results

# 8. Pagination models work
python -c "from src.core.pagination import PaginatedResponse, paginate; print('Pagination OK')"

# 9. Response models work
python -c "from src.core.responses import ApiResponse, ErrorResponse; print('Responses OK')"

# 10. Exception hierarchy complete
python -c "from src.core.exceptions import WandrError, NotFoundError, WandrLLMError; print('Exceptions OK')"

# 11. Health endpoint responds
curl -s http://localhost:8000/api/v1/health | python -m json.tool
# Expected: {"success": true, "data": {"status": "ok", ...}}

# 12. Docker infra running
docker compose ps
# Expected: both wandr_postgres and wandr_qdrant running/healthy
```

All 12 checks passing → P0 is done. Proceed to P1.