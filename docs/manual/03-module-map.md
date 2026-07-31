# 03 — Module map (through P5.11)

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [02-layers](02-layers.md)

Source of truth for “real vs stub”: [`docs/context.md`](../context.md). This page is a navigable snapshot as of **P5.11**.

---

## Package tree (mental map)

```text
src/
├── main.py                 # App factory ✅ (auth + destinations + places; CORS; Qdrant/embed lifespan)
├── config.py               # Settings ✅ (incl. Qdrant, embeddings, CORS, planner timeouts)
├── auth/                   # Google OAuth + JWT cookie flow ✅ (deps.py stub)
├── geo/                    # schemas, geocoder, overpass, osrm ✅
├── core/                   # shared infrastructure ✅
│   ├── database/           # base, session, BaseRepository ✅
│   ├── security/           # jwt, permissions ✅
│   ├── middleware/         # logging, rate_limit (path table) ✅
│   ├── observability/      # logging, tracing ✅
│   ├── llm/                # litellm gateway ✅ (chat_completion + chat_with_tools)
│   ├── pagination.py ✅
│   ├── responses.py ✅
│   └── exceptions.py ✅
├── destinations/           # models…router + readiness ✅ (search_available live)
├── places/                 # models…router + enrich_place ✅ (tags + enriched_tags)
├── search/                 # Qdrant client, embeddings, places_index ✅
├── travel_engine/          # pure selector→…→validator ✅ (no I/O)
├── planner/                # tools + graph loop ✅ · service SSE bridge ❌ (5.12) · HTTP ❌ (P6)
├── trips/                  # models ✅ · HTTP ❌ stubs
└── evaluation/             # models + generation repo/service ✅ · HTTP ❌

alembic/                    # migrations 001–004 ✅
scripts/                    # P1/P2/P4 smoke + geo CLIs + seed + enrich + index ✅
tests/                      # core + auth + geo + destinations + places + scripts + search + travel_engine + planner ✅
```

---

## Real modules (implemented)

### App & config

| Path | Exports / role |
|------|----------------|
| `src/main.py` | `create_app()`, lifespan (DB + Qdrant ensure + MiniLM), CORSMiddleware, handlers, health + auth + destinations + places |
| `src/config.py` | `get_settings()` — DB, OAuth, JWT, rate limits, geo, Qdrant, embeddings, enrich concurrency, CORS, planner ceilings |

### Core

| Path | Exports / role |
|------|----------------|
| `src/core/observability/logging.py` | `configure_logging()`, `get_logger()` |
| `src/core/observability/tracing.py` | `get_tracer()`, `flush_tracer()` |
| `src/core/llm/client.py` | `chat_completion()`, `chat_with_tools()` — **only** litellm import site |
| `src/core/pagination.py` | `PageParams`, `PaginatedResponse[T]`, `paginate()` |
| `src/core/responses.py` | `ApiResponse[T]`, `ErrorResponse` |
| `src/core/exceptions.py` | `WandrError` hierarchy |
| `src/core/database/base.py` | `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` |
| `src/core/database/session.py` | `get_engine()`, `get_session_factory()`, `get_db()`, `ping_db()`, `dispose_engine()` |
| `src/core/database/base_repository.py` | `BaseRepository[ModelT, IDT]` — soft-delete, flush-only |
| `src/core/security/jwt.py` | `TokenPayload`, `create_access_token()`, `verify_token()` |
| `src/core/security/permissions.py` | `require_auth`, `optional_auth`, `get_current_user_id` |
| `src/core/middleware/logging.py` | `RequestLoggingMiddleware` |
| `src/core/middleware/rate_limit.py` | `RateLimitMiddleware`, path table (planner 10/min, destinations/search 20/min) |

### Auth

| Path | Exports / role |
|------|----------------|
| `src/auth/models.py` | `User` |
| `src/auth/schemas.py` | `UserOut`, `AuthMeResponse`, `TokenResponse`, … |
| `src/auth/exceptions.py` | OAuth / token / inactive errors |
| `src/auth/repository.py` | `UserRepository` |
| `src/auth/service.py` | `AuthService` — Google exchange, upsert |
| `src/auth/router.py` | `/api/v1/auth/google\|callback\|me\|logout` |

### Destinations & places

| Path | Exports / role |
|------|----------------|
| `src/destinations/models.py` | `Destination` |
| `src/destinations/schemas.py` | `DestinationOut`, `DestinationSearchQuery`, `DestinationReadinessOut` |
| `src/destinations/exceptions.py` | `DestinationNotFoundError` (404) |
| `src/destinations/repository.py` | `DestinationRepository` — atomic upsert, ILIKE search |
| `src/destinations/service.py` | `DestinationService` — cache-aside search + `get_readiness` |
| `src/destinations/readiness.py` | `compute_readiness`, `ReadinessResult` — pure, no I/O |
| `src/destinations/router.py` | `/api/v1/destinations/search`, `/{id}/readiness` |
| `src/places/models.py` | `Place` — `tags` (OSM) + `enriched_tags` (LLM list) + POINT |
| `src/places/constants.py` | `PLACE_TAG_VOCAB` |
| `src/places/schemas.py` | `PlaceOut` — lat/lng via `to_shape` |
| `src/places/repository.py` | `PlaceRepository` — upsert, geography radius, list/count |
| `src/places/service.py` | `PlaceService` — list/get + `enrich_place` |
| `src/places/router.py` | `/api/v1/places`, `/api/v1/places/{id}` |

### Search (P3)

| Path | Exports / role |
|------|----------------|
| `src/search/client.py` | `AsyncQdrantClient`, `ensure_places_collection`, `is_qdrant_available` |
| `src/search/embeddings.py` | MiniLM lifespan load; `embed_text` / `embed_batch` |
| `src/search/places_index.py` | batch upsert + destination-scoped `search_places`, `count_indexed` |

### Travel engine (P4) — pure Python, no I/O

| Path | Exports / role |
|------|----------------|
| `src/travel_engine/protocols.py` | `RouteLeg`, `RoutingProvider`, `legs_to_lookup` |
| `src/travel_engine/travel_rules.py` | Caps, structural durations, interest weights, `visit_duration_min` |
| `src/travel_engine/place_selector.py` | `score_place`, `select_places`, `explain_selection`, … |
| `src/travel_engine/day_allocator.py` | `allocate_days` — cluster + caps/budget |
| `src/travel_engine/route_optimizer.py` | `optimize_route`, `OptimizeResult`, `DroppedStop` |
| `src/travel_engine/schedule_builder.py` | `build_day_schedule`, `ScheduledStop` |
| `src/travel_engine/trip_validator.py` | `validate_trip`, `ValidationResult`, `DayPlan`, `TripItinerary` |

### Planner tools + graph (P5.1–5.11)

| Path | Exports / role |
|------|----------------|
| `src/planner/routing_provider.py` | `OsrmRoutingProvider` — wraps `geo/osrm.get_route` → `RouteLeg` |
| `src/planner/tools/schemas.py` | `AgentPhase`, `PHASE_TOOLS`, `DEFAULT_TOOL_BY_PHASE`, `ToolResult`, `ToolContext`, 12 input models |
| `src/planner/tools/registry.py` | 12-tool `TOOL_REGISTRY`, phase-gated `execute_tool`, `parse_tool_input` |
| `src/planner/tools/orchestration.py` | `check_preconditions`, `apply_tool_result` (sole writer), `maybe_transition_phase`, `run_stuck_detector` |
| `src/planner/tools/constants.py` | Rank/search defaults |
| `src/planner/tools/*.py` (12) | Real tool bodies → `ToolResult` only (no TravelState mutation) |
| `src/planner/graph/state.py` | `TravelState` TypedDict — no db/routing; list fields last-write-wins |
| `src/planner/graph/messages.py` | `build_agent_messages` — phase + PHASE_TOOLS + compact summary |
| `src/planner/graph/nodes/parse_preferences.py` | Fixed `chat_completion` prefs bookend; defaults on LLM fail |
| `src/planner/graph/nodes/agent.py` | Sets `pending_tool_calls` only; never calls `execute_tool` |
| `src/planner/graph/nodes/tool_executor.py` | Sole `execute_tool` caller; apply + stuck-detector |
| `src/planner/graph/nodes/write_narrative.py` | Titles/paragraphs via LLM; templates on fail; geometry locked |
| `src/planner/graph/nodes/record_evaluation.py` | Best-effort `EvaluationService.record_generation` |
| `src/planner/graph/builder.py` | `build_planner_graph` / `get_compiled_graph` singleton |

### Evaluation (generation persist)

| Path | Exports / role |
|------|----------------|
| `src/evaluation/models.py` | `TripEvaluation` |
| `src/evaluation/repository.py` | `EvaluationRepository` — flush-only create |
| `src/evaluation/service.py` | `record_generation(state)` maps TravelState → columns |

### Domain models only (no HTTP yet)

| Path | Model |
|------|-------|
| `src/trips/models.py` | `Trip`, `TripPlace`, `TripEditEvent`, enums |

### Geo

| Path | Exports / role |
|------|----------------|
| `src/geo/schemas.py` | `GeocodedPlace`, `RawPOI`, `RouteResult` |
| `src/geo/geocoder.py` | `geocode()` |
| `src/geo/overpass.py` | `fetch_pois()` |
| `src/geo/osrm.py` | `get_route()` — OSRM + haversine × 1.4 fallback |

### Migrations & tooling

| Path | Role |
|------|------|
| `alembic/env.py` | Async Alembic + model imports |
| `alembic/versions/001_enable_postgis.py` | PostGIS + uuid-ossp |
| `alembic/versions/20260717_*_create_all_tables.py` | Core tables |
| `alembic/versions/20260721_*_add_trip_edit_events.py` | `trip_edit_events` |
| `alembic/versions/20260728_*_add_place_enriched_tags.py` | `places.enriched_tags` |
| `scripts/test_db_conn.py` | DB ping |
| `scripts/test_p1_smoke.py` | P1 smoke |
| `scripts/test_p2_smoke.py` | Live P2 proof (network + commits seed data) |
| `scripts/test_p4_smoke.py` | Offline Fake travel_engine pipeline (+ optional live OSRM) |
| `scripts/test_geocoder.py` | Live Nominatim CLI |
| `scripts/test_overpass.py` | Live Overpass CLI |
| `scripts/seed_destination.py` | Seed CLI — `seed_destination()`, `seed_destination_into()`, `seed_places()` |
| `scripts/enrich_places.py` | LLM enrich batch (savepoint per place) |
| `scripts/index_places.py` | Qdrant + embeddings index batch |
| `tests/core/`, `tests/auth/` | P0/P1 pytest |
| `tests/geo/`, `tests/destinations/`, `tests/places/`, `tests/scripts/` | P2 pytest |
| `tests/search/` | P3 search/embeddings tests |
| `tests/travel_engine/`, `tests/planner/` | P4 purity + P5 phase transitions / tools (tool-loop suite lands 5.13) |

---

## Stubs only (no public API — do not invent imports)

| Area | Notes |
|------|-------|
| `src/auth/dependencies.py` | Unused placeholder |
| `src/trips/*` except `models.py` | Trip HTTP CRUD later (P6+) |
| `src/planner/service.py` | SSE bridge / `generate` — **5.12** (not context-✅ yet); do not treat as shipped API |
| Planner HTTP `POST /api/v1/planner/generate` | **P6** — not registered in `main.py` |
| Clarification-path evaluation | Graph ends clarification at END without `record_evaluation`; deferred to 5.12 service |

If unsure: open the file. Stubs are ~1-line docstrings. Planner **tools** + **orchestration** + **graph nodes/builder** (5.1–5.11) are **real**.

Next: [04 — Imports & wiring](04-imports-and-wiring.md)
