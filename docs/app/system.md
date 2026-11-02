# Wandr Backend — System Context

> Architecture deep reference for the Wandr FastAPI backend (modular monolith, phase-gated tool-loop agent).
> Guardrails: `[AGENT.md](../../AGENT.md)`. Step progress / stubs / live routes: `[docs/context.md](../context.md)`. Build contracts: `[docs/blueprint_final.md](../blueprint_final.md)` (P0–P7), `[docs/v2_blueprint.md](../v2_blueprint.md)` (v7). Patterns: `[docs/app/lld.md](lld.md)`. API contract for FE: `[docs/FE_guide.md](../FE_guide.md)`. Package versions: `requirements.txt`.

## What Wandr Does

Wandr generates structured multi-day travel itineraries. Users describe preferences in natural language; the backend:

1. Resolves destinations and checks data readiness (catalog search / prepare / readiness)
2. Searches and ranks places (hybrid dense + sparse RRF, with dense-only kill-switch)
3. Builds routes and day schedules via deterministic `travel_engine` logic
4. Orchestrates via a bounded LangGraph agent with typed, phase-gated tools
5. Writes narrative copy via LLM (outside the tool loop)
6. Persists trips (including day edit/replan) and records every generation/edit for evaluation

**Core principle:** structure from code, narrative from LLM. Place IDs, coordinates, stop order, and times never come from free-form LLM output.

## Architecture Overview

```
Client (HTTP/SSE)
    │
    ▼
FastAPI Routers          ← ApiResponse[T] / PaginatedResponse[T]; CORS; request-ID + rate limits
    │
    ▼
Domain Services          ← business logic, orchestration
    │
    ├──► Repositories    ← SQLAlchemy async, PostGIS
    ├──► travel_engine/  ← pure Python, no I/O (RoutingProvider injected)
    ├──► planner/tools/  ← TOOL_REGISTRY + execute_tool(); apply_tool_result sole state writer
    ├──► geo/            ← Nominatim, Overpass (+ optional POI sources), OSRM gateways
    ├──► search/         ← Qdrant (places_v2 named vectors) + embeddings (+ sparse/RRF)
    ├──► core/llm/       ← LiteLLM gateway (only LLM entry point)
    ├──► core/cache/     ← CacheBackend (Redis or in-memory)
    └──► evaluation/     ← generation persist + mark_trip_edited (HTTP still stub)
```

## Repository Layout


| Path                 | Role                                                                        |
| -------------------- | --------------------------------------------------------------------------- |
| `src/config.py`      | Env SSOT via `get_settings()`                                               |
| `src/core/`          | DB, security/JWT, middleware, cache, observability, LLM gateway, envelopes  |
| `src/auth/`          | Google OAuth + JWT cookie/Bearer; user upsert                               |
| `src/destinations/`  | Catalog search/resolve, readiness, public prepare (ingest)                  |
| `src/places/`        | POI storage, enrich (`enriched_tags`), HTTP list/get                        |
| `src/trips/`         | Persist from planner state; CRUD / GeoJSON / claim; day edit/replan HTTP    |
| `src/planner/`       | Tools + LangGraph + `PlannerService.generate` + SSE `/generate` + MVP cache |
| `src/travel_engine/` | Pure select / allocate / optimize / schedule / validate                     |
| `src/geo/`           | Geocoder, Overpass (+ multi-source facade), OSRM                            |
| `src/search/`        | Embeddings, sparse encode, Qdrant client, hybrid `search_places`            |
| `src/evaluation/`    | Models + repo/service for generation/edit flags — **no evaluation HTTP**    |
| `scripts/`           | Seed / enrich / index / smokes / `run_evals.py`                             |
| `tests/`             | Pytest per domain (`wandr_test`)                                            |
| `.github/workflows/` | CI (pytest + image build); deploy is `workflow_dispatch`                    |


## Request Path

1. Middleware: CORS → request logging (`X-Request-ID`) → rate limits (path + IP; Redis or in-memory).
2. Router validates input, applies auth deps (`require_auth` / `optional_auth`), returns `ApiResponse[T]` or `PaginatedResponse[T]` only.
3. Service owns business rules and UoW commits; repository is flush-only CRUD (soft-delete aware where applicable).
4. External I/O only via gateways (`geo/`, `core/llm/`, Qdrant client) with timeouts, tenacity retry, and named fallbacks.
5. Global handlers map `WandrError` → `ErrorResponse`; unhandled → generic 500 (traceback logged).

## Planner (tool-loop agent)

- **Phases + tools:** `AgentPhase` / `PHASE_TOOLS`; 12-tool `TOOL_REGISTRY`; phase-gated `execute_tool`. Tools return `ToolResult` only; `apply_tool_result` is the sole TravelState writer from tools.
- **Graph:** `parse_preferences` → agent ↔ tool_executor loop → `write_narrative` / `record_evaluation` bookends. Agent sets `pending_tool_calls` only; `tool_executor_node` is the sole `execute_tool` caller. Stuck-detector and tool-call ceiling bound the loop.
- **HTTP:** `POST /api/v1/planner/generate` SSE — readiness floor (409), absolute timeout ceiling, terminal buffer → `TripService.save_from_state` + `trip_id`. Optional auth + `wandr_session` cookie. Clients use `fetch()` + manual SSE (not `EventSource`); proxies must not buffer this path.
- **Cache:** MVP planner cache via `CacheBackend`; cache hit still persists a new trip.

## Search and place knowledge

- Enrich places (`PLACE_TAG_VOCAB`) → index into Qdrant.
- Active collection via `places_collection()` — typically `places_v2` with named `dense` + `bm25` vectors and hybrid RRF (`SEARCH_SPARSE_ENABLED` kill-switch → dense-only).
- Optional fusion diagnostics into `tool_trace` (`SEARCH_FUSION_DIAGNOSTICS`).
- Embeddings: local MiniLM or hosted via LiteLLM (`PLACES_EMBEDDING_BACKEND`).

## Routing backends

`get_routing_provider()` selects on `ROUTING_BACKEND`:


| Value                 | Matrix / times                | Polylines / GeoJSON                        |
| --------------------- | ----------------------------- | ------------------------------------------ |
| `haversine` (default) | In-process haversine × factor | Point-only GeoJSON                         |
| `hybrid`              | Haversine times               | OSRM fail-soft polylines → map LineStrings |
| `osrm`                | Live pairwise OSRM matrix     | Live polylines (spike / self-host)         |


`travel_engine` stays pure; times and polylines are injected. Shared `populate_leg_polylines` used by optimize and day reoptimize.

## Trips

- **Generate path:** `save_from_state` UoW from planner terminal state (ownership / guest session).
- **HTTP:** list/get/delete, public GeoJSON, claim, plus four day-edit routes (reorder / remove / add / reoptimize) with owner auth + user-keyed `rate_limit_trip_edit`.
- **Edits:** TripService day surgery + preserve-order schedule; `TripEditEvent` + `EvaluationService.mark_trip_edited` in the same UoW. Concurrent edits are last-write-wins (MVP).

## Observability and evals

- **Logging:** structlog (`configure_logging` / `get_logger`); request-id contextvars.
- **Tracing:** `get_tracer()` → Langfuse when keys set, else `NoOpTracer`. Parent generate trace + tool spans around `PlannerService.generate` (fail-soft).
- **Usage:** `LLMUsage` / `TravelState.token_usage` through the LLM gateway.
- **Golden harness:** `evals/` + `scripts/run_evals.py` + `src/evaluation/scorers.py` (generate-mode baseline).

## Local Development Infrastructure

`docker-compose.yml` is **dev-only** (never production):


| Service          | Typical host port | Purpose                                                                 |
| ---------------- | ----------------- | ----------------------------------------------------------------------- |
| `wandr_postgres` | 5433              | PostGIS                                                                 |
| `wandr_qdrant`   | 6335 / 6336       | Vector search                                                           |
| Redis            | 6380              | Rate limit + planner cache (Compose API injects `redis://redis:6379/0`) |
| `wandr_api`      | 8000              | Uvicorn reload (`--reload-dir` src)                                     |


Empty host `REDIS_URL` keeps rate limit + planner cache **in-memory** (fine for pytest / single-process host uvicorn; not shared across workers). Compose API sets Redis; optional host uvicorn: `redis://localhost:6380/0`.

Production uses hosted services + `docker-compose.prod.yml` / `ops/*.sh` — see `[docs/steps/blueprint_production.md](../steps/blueprint_production.md)`.

```bash
docker compose up --build
# Health: http://localhost:8000/api/v1/health
# OpenAPI: http://localhost:8000/docs
```

Host URLs: Postgres `…@localhost:5433/wandr`, Qdrant `http://localhost:6335`. `LLM_API_KEY` optional for catalog/health; required for generate/enrich.

## Configuration

All env access through `get_settings()` — never `os.environ.get()` in feature code. Key groups: Core, Database, Vector search / hybrid flags, Cache (`REDIS_URL`), LLM, Planner bounds / timeout, Observability (`LANGFUSE_*`), Geo (`PLACES_SOURCES`, Nominatim/Overpass/OSRM), CORS, routing (`ROUTING_BACKEND`). See `.env.example`.

## HTTP surface (summary)

Registered under `/api/v1`: health, auth (Google OAuth + me/logout), destinations (search / resolve / readiness / prepare), places (list/get), planner `POST /generate` (SSE), trips (CRUD / GeoJSON / claim / day edits).

Full auth matrix and DTOs: `[docs/FE_guide.md](../FE_guide.md)`. Exact table: `[docs/context.md](../context.md)` → Live endpoints.

## Stubs and deferred


| Item                                         | Status                                                                                 |
| -------------------------------------------- | -------------------------------------------------------------------------------------- |
| Evaluation HTTP                              | Stub — generation persist + `mark_trip_edited` are real                                |
| `src/auth/dependencies.py`                   | Still step 0.1 placeholders (real auth deps live under `core/security`)                |
| V6.2 / V6.3 (embedding bump / cross-encoder) | Deferred — not retrieval-dominant                                                      |
| Clarification path graph `record_evaluation` | Clarification ends without that graph node; service still records after invoke/timeout |


Do not invent public APIs for stub rows.

## Build status (rollup)

**P0–P7 + v7 V0–V6.1 ✅.** V6.2/V6.3 deferred. **Next:** first VPS deploy (`ops/migrate.sh` → `deploy.sh` → `health.sh`), then FE → staging API URL.

Step-level Progress and Implemented modules live only in `[docs/context.md](../context.md)` — do not treat this file as a changelog.

## Key Constraints for AI Agents

1. Read `AGENT.md` first; then `docs/context.md` for what is real vs stub
2. All env via `get_settings()`
3. Router → Service → Repository only
4. External calls behind gateways with timeout, retry, and named fallback
5. Record evaluation on every planner generation (and edits via trip edit UoW)
6. New packages → `requirements.txt` with a why-comment
7. Prefer this doc for architecture shape; prefer `context.md` for “is it built?”

