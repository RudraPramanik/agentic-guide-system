# 04 — Imports & wiring

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [03-module-map](03-module-map.md)

Focus: **who imports whom** for code that exists today. Stub packages are omitted on purpose.

---

## App startup & HTTP

```mermaid
flowchart TD
  U[uvicorn src.main:app] --> M[src/main.py create_app]
  M --> CFG[src/config.py get_settings]
  M --> LOG[core/observability/logging]
  M --> DB[core/database/session ping_db dispose_engine]
  M --> MW0[CORSMiddleware]
  M --> MW1[RequestLoggingMiddleware]
  M --> MW2[RateLimitMiddleware]
  M --> AR[auth/router]
  M --> DR[destinations/router]
  M --> PR[places/router]
  M --> H["GET /api/v1/health"]
  M --> QD[search ensure + embeddings load]
```

| From | Imports | Why |
|------|---------|-----|
| `src/main.py` | `get_settings` | Env / app metadata / CORS origins |
| `src/main.py` | `configure_logging`, `get_logger` | Lifespan logging |
| `src/main.py` | `ping_db`, `dispose_engine` | DB health + shutdown |
| `src/main.py` | `ensure_places_collection`, embedding load | Qdrant + MiniLM lifespan |
| `src/main.py` | `WandrError`, `ApiResponse`, `ErrorResponse` | Global handlers |
| `src/main.py` | `CORSMiddleware`, `RequestLoggingMiddleware`, `RateLimitMiddleware` | Cross-cutting |
| `src/main.py` | `auth.router`, `destinations.router`, `places.router` | Mount HTTP routes |

---

## Auth request chain

```mermaid
flowchart LR
  R[auth/router.py] --> S[auth/service.py]
  S --> UR[auth/repository.py]
  UR --> BR[core/database/base_repository.py]
  UR --> UM[auth/models.py]
  R --> JWT[core/security/jwt.py]
  R --> PERM[core/security/permissions.py]
  R --> DB[(get_db session)]
  S --> CFG[get_settings]
  S --> HTTP[httpx Google OAuth]
```

| From | Imports | Why |
|------|---------|-----|
| `auth/router.py` | `AuthService` | Business operations |
| `auth/router.py` | `get_db` | Session dependency |
| `auth/router.py` | `optional_auth`, `create_access_token` | Cookie/Bearer + JWT issue |
| `auth/router.py` | `ApiResponse`, schemas, exceptions | HTTP envelope |
| `auth/service.py` | `UserRepository` | Persistence |
| `auth/service.py` | `get_settings`, httpx, tenacity | Google token/userinfo |
| `auth/repository.py` | `User`, `BaseRepository` | Soft-delete CRUD |
| `auth/models.py` | `Base` + mixins | ORM table |
| `auth/exceptions.py` | `WandrError` subclasses | Domain errors |

**Do not:** import `UserRepository` from the router. Router → Service → Repository only.

---

## Geo gateways

```mermaid
flowchart TD
  CLI1[scripts/test_geocoder.py] --> G[geo/geocoder.py geocode]
  CLI2[scripts/test_overpass.py] --> O[geo/overpass.py fetch_pois]
  G --> SCH1[geo/schemas.py GeocodedPlace]
  O --> SCH2[geo/schemas.py RawPOI]
  G --> CFG[get_settings]
  O --> CFG
  G --> LOG[get_logger]
  O --> LOG
  G --> NOM[Nominatim HTTP]
  O --> OVP[Overpass HTTP]
```

| From | Imports | Why |
|------|---------|-----|
| `geo/geocoder.py` | `get_settings`, `get_logger`, `GeocodedPlace` | Config, logs, DTO |
| `geo/overpass.py` | `get_settings`, `get_logger`, `RawPOI` | Config, logs, DTO |
| `geo/schemas.py` | pydantic only | No FastAPI / SQLAlchemy |
| `scripts/seed_destination.py`, `destinations/service.py` | `geocode` / `fetch_pois` only | Never raw OverpassQL or Nominatim URLs outside `geo/` |
| Callers needing driving times | `geo/osrm.get_route` | Haversine × 1.4 fallback; never raises httpx |

---

## Seed pipeline (P2.4)

```mermaid
flowchart TD
  CLI[scripts/seed_destination.py] --> G[geo/geocoder.py geocode]
  CLI --> O[geo/overpass.py fetch_pois]
  CLI --> DR[destinations/repository.py upsert_from_geocoded]
  CLI --> PR[places/repository.py upsert_from_poi]
  CLI --> SES[core/database/session AsyncSessionLocal]
  DR --> BR[core/database/base_repository.py]
  PR --> BR
  CLI --> COMMIT[(session.commit)]
```

| From | Imports | Why |
|------|---------|-----|
| `scripts/seed_destination.py` | `geocode`, `fetch_pois` | Only sanctioned outbound geo path |
| `scripts/seed_destination.py` | `DestinationRepository`, `PlaceRepository` | Atomic upserts (`ON CONFLICT`) |
| `scripts/seed_destination.py` | `AsyncSessionLocal`, `dispose_engine` | Owns the session; scripts commit |
| `scripts/seed_destination.py` | `configure_logging`, `get_logger` | `seed.poi_failed` / `seed.no_pois` warnings |

Contract worth knowing before you touch it: each POI upsert runs inside `session.begin_nested()`
(a SAVEPOINT), so one failing row is rolled back and skipped while the rest of the batch and the
final commit still succeed. A bare `try/except` would leave the Postgres transaction aborted.

`seed_places(session, destination_id, pois) -> int` and
`seed_destination_into(session, name, radius_km)` are importable on purpose —
pytest drives failure boundaries without the CLI owning the session. The CLI
wrapper (`seed_destination`) still opens `AsyncSessionLocal`, commits, and
returns exit codes.

---

## Destination search + readiness (P2.6c / 2.8)

```mermaid
flowchart LR
  R[destinations/router.py] --> S[destinations/service.py]
  S --> REP[destinations/repository.py]
  S --> G[geo/geocoder.py geocode]
  S --> RD[destinations/readiness.py compute_readiness]
  S --> EX[DestinationNotFoundError]
  REP --> BR[core/database/base_repository.py]
```

DB hit returns early and never calls Nominatim; only a miss geocodes, upserts atomically, and
commits. Readiness is pure math over denormalized counters; `search_available` is the live
`is_qdrant_available()` flag (P3.6), not permanently False.

---

## Places HTTP (P2.7b)

```mermaid
flowchart LR
  PR[places/router.py] --> PS[places/service.py]
  PS --> PREP[places/repository.py]
  PS --> DREP[destinations/repository.py]
  PS --> SCH[places/schemas.py PlaceOut]
```

List verifies the destination exists first (404, never empty page). Router never touches repositories.
`PlaceService.enrich_place` (P3) writes `enriched_tags` via the LLM gateway — still Router→Service→Repo for HTTP.

---

## Search + enrich / index (P3)

```mermaid
flowchart TD
  ENR[scripts/enrich_places.py] --> PS[places/service.py enrich_place]
  PS --> LLM[core/llm/client.py]
  PS --> PREP[places/repository.py]
  IDX[scripts/index_places.py] --> PI[search/places_index.py]
  PI --> EMB[search/embeddings.py]
  PI --> QC[search/client.py AsyncQdrantClient]
  RD[destinations/service get_readiness] --> AVAIL[search/client is_qdrant_available]
```

| From | Imports | Why |
|------|---------|-----|
| `search/client.py` | `get_settings`, Qdrant async client | Fail-soft collection ensure |
| `search/embeddings.py` | sentence-transformers via lifespan | `embed_text` / `embed_batch` off event loop |
| `search/places_index.py` | client + embeddings | Destination-scoped upsert / search |
| Enrich/index scripts | services / search modules | Batch CLIs; savepoint per item where needed |

---

## Travel engine + planner envelope (P4)

```mermaid
flowchart TD
  SEL[travel_engine/place_selector] --> ALL[day_allocator]
  ALL --> OPT[route_optimizer]
  OPT --> SCH[schedule_builder]
  SCH --> VAL[trip_validator]
  OPT --> RP[RoutingProvider protocol]
  ORP[planner/routing_provider OsrmRoutingProvider] --> OSRM[geo/osrm get_route]
  ORP -.->|implements| RP
```

| From | Imports | Why |
|------|---------|-----|
| `travel_engine/*` | each other + `protocols` / `travel_rules` only | **No** geo / DB / LLM imports |
| `route_optimizer` | `RoutingProvider` protocol | Times injected by caller |
| `OsrmRoutingProvider` | `geo/osrm.get_route` → `RouteLeg` | Adapter at planner boundary |

`scripts/test_p4_smoke.py` drives the pure pipeline with a Fake routing provider (optional live OSRM).

---

## Planner tool loop + graph (P5.1–5.11)

```mermaid
flowchart TD
  PP[parse_preferences] --> AG[agent_node]
  AG -->|pending_tool_calls| TE[tool_executor_node]
  TE -->|execute_tool + apply_tool_result| AG
  AG -->|plan_complete / abort| WN[write_narrative]
  WN --> RE[record_evaluation]
  TE --> REG[tools/registry execute_tool]
  REG --> BODY[tool bodies]
  BODY --> TE_ENG[travel_engine / search / geo via tools]
  AG --> LLM[core/llm chat_with_tools]
  PP --> LLM2[core/llm chat_completion]
  WN --> LLM2
  RE --> EV[evaluation/service record_generation]
  BLD[graph/builder get_compiled_graph] --> PP
```

| From | Imports | Why |
|------|---------|-----|
| `agent_node` | `chat_with_tools`, `build_agent_messages`, `PHASE_TOOLS` | Decides tools only — **never** `execute_tool` |
| `tool_executor_node` | `execute_tool`, `apply_tool_result`, stuck-detector | Sole tool runner; optional `emit` later (5.12) |
| `execute_tool` | `TOOL_REGISTRY` + phase/precondition gates | Typed contracts; tools return `ToolResult` only |
| `apply_tool_result` | orchestration sole writer | Tools never mutate `TravelState` |
| Graph nodes | `ToolContext` from `config["configurable"]` | Cached compiled graph shared across requests |
| `record_evaluation` | `EvaluationService` | Best-effort persist; warning on DB fail |
| `builder` | LangGraph compile singleton | agent→executor unconditional; bookends on complete |

Clarification exit ends at END **without** `record_evaluation` (deferred to 5.12 service).

---

## Database & models

| From | Imports | Why |
|------|---------|-----|
| Domain `*/models.py` | `src.core.database.base` mixins | Shared UUID / timestamps / soft-delete |
| `alembic/env.py` | All model modules | Autogenerate / metadata |
| Repositories | models + `BaseRepository` | Typed CRUD |
| Routers needing DB | `get_db` only (via service today) | Session scope |

---

## Security helpers

| From | Imports | Why |
|------|---------|-----|
| `permissions.py` | `jwt.verify_token` | Parse Bearer / cookie |
| Routers | `require_auth` / `optional_auth` | FastAPI dependencies |
| Auth callback | `create_access_token` | Issue `wandr_token` |

---

## What is *not* wired yet

- `PlannerService.generate` SSE bridge (5.12) — not context-✅; `/api/v1/planner/generate` HTTP is **P6** (not in `main.py`).
- Trips HTTP CRUD — models only.
- Clarification-path evaluation persist — deferred to 5.12 service.

Search, travel_engine, and the full P5 planner tools + graph loop **are** wired — see sections above.

## P2–P5 verification wiring

| Path | Role |
|------|------|
| `tests/geo/` | Mocked Nominatim / Overpass / OSRM gateway tests |
| `tests/destinations/`, `tests/places/` | Readiness, repository, and HTTP router tests |
| `tests/scripts/test_seed_destination.py` | Seed failure boundaries via `seed_destination_into` / `seed_places` |
| `scripts/test_p2_smoke.py` | Live fail-fast proof (network + commits to the development database) |
| `tests/search/` | Qdrant / embeddings / index tests |
| `tests/travel_engine/`, `tests/planner/` | Purity + phase transitions + tools; full tool-loop suite lands 5.13 |
| `scripts/test_p4_smoke.py` | Offline Fake travel_engine pipeline (+ optional live OSRM) |
| `scripts/test_agent.py` | P5 agent smoke — lands with 5.14 (not context-✅ yet) |

Next: [05 — How to change](05-how-to-change.md)
