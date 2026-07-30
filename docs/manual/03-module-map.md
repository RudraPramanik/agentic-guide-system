# 03 — Module map (through P4.10)

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [02-layers](02-layers.md)

Source of truth for “real vs stub”: [`docs/context.md`](../context.md). This page is a navigable snapshot as of **P4.10**.

---

## Package tree (mental map)

```text
src/
├── main.py                 # App factory ✅ (auth + destinations + places; CORS; Qdrant/embed lifespan)
├── config.py               # Settings ✅ (incl. Qdrant, embeddings, CORS, enrich concurrency)
├── auth/                   # Google OAuth + JWT cookie flow ✅ (deps.py stub)
├── geo/                    # schemas, geocoder, overpass, osrm ✅
├── core/                   # shared infrastructure ✅
│   ├── database/           # base, session, BaseRepository ✅
│   ├── security/           # jwt, permissions ✅
│   ├── middleware/         # logging, rate_limit (path table) ✅
│   ├── observability/      # logging, tracing ✅
│   ├── llm/                # litellm gateway ✅
│   ├── pagination.py ✅
│   ├── responses.py ✅
│   └── exceptions.py ✅
├── destinations/           # models…router + readiness ✅ (search_available live)
├── places/                 # models…router + enrich_place ✅ (tags + enriched_tags)
├── search/                 # Qdrant client, embeddings, places_index ✅
├── travel_engine/          # pure selector→…→validator ✅ (no I/O)
├── planner/                # routing_provider + tools envelope ✅ · LangGraph / tool bodies ❌
├── trips/                  # models ✅ · rest ❌ stubs
└── evaluation/             # models ✅ · rest ❌ stubs

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
| `src/config.py` | `get_settings()` — DB, OAuth, JWT, rate limits, geo, Qdrant, embeddings, enrich concurrency, CORS origins |

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

### Planner envelope (P4 — not the graph yet)

| Path | Exports / role |
|------|----------------|
| `src/planner/routing_provider.py` | `OsrmRoutingProvider` — wraps `geo/osrm.get_route` → `RouteLeg` |
| `src/planner/tools/schemas.py` | `ToolResult` envelope |
| `src/planner/tools/registry.py` | `execute_tool` stub — unknown → `ok=False` (full registry P5) |

### Domain models only (no services yet)

| Path | Model |
|------|-------|
| `src/trips/models.py` | `Trip`, `TripPlace`, `TripEditEvent`, enums |
| `src/evaluation/models.py` | `TripEvaluation` |

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
| `tests/travel_engine/`, `tests/planner/` | P4 purity + adapter/envelope tests |

---

## Stubs only (no public API — do not invent imports)

| Area | Notes |
|------|-------|
| `src/auth/dependencies.py` | Unused placeholder |
| `src/trips/*` except `models.py` | Trip APIs later |
| `src/evaluation/*` except `models.py` | Eval recording later |
| Planner LangGraph / tool *bodies* | P5 — nodes, graph builder, tool impls beyond envelope |
| Full `TOOL_REGISTRY` tool functions | Envelope exists; bodies land in P5 |

If unsure: open the file. Stubs are ~1-line docstrings. Do **not** treat `src/search/` or `src/travel_engine/` as stubs — they are real.

Next: [04 — Imports & wiring](04-imports-and-wiring.md)
