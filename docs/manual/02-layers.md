# 02 — Layers & AI boundary

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [01-orientation](01-orientation.md)

Hard rules live in [`AGENT.md`](../../AGENT.md). This page explains **why** the layers exist.

---

## Request path (implemented today)

```text
Client
  │
  ▼
Middleware (outer → inner as registered)
  RequestLoggingMiddleware   ← X-Request-ID, latency logs
  RateLimitMiddleware        ← per-IP limits (fail-open)
  │
  ▼
Router  (e.g. auth / destinations / places routers, /api/v1/health)
  │  returns ApiResponse[T] or PaginatedResponse[T]
  ▼
Service (e.g. AuthService)
  │  business logic, orchestration, external HTTP (OAuth)
  ▼
Repository (e.g. UserRepository → BaseRepository)
  │  SQLAlchemy async, flush-only writes
  ▼
Postgres / PostGIS
```

**Why this order?**

| Layer | Owns | Must not |
|-------|------|----------|
| Router | HTTP shape, auth deps, status codes | Touch DB / SQLAlchemy sessions for business writes directly |
| Service | Use-cases, retries for domain externals (e.g. Google) | Be imported by repositories |
| Repository | Queries, upserts, soft-delete awareness | Know about FastAPI Request / HTTP |

---

## Cross-cutting “core”

| Concern | Module | Why it exists |
|---------|--------|---------------|
| Settings | `src/config.py` → `get_settings()` | Single env access; no scattered `os.environ` |
| Logging | `src/core/observability/logging.py` | Structured logs + request context |
| Tracing | `src/core/observability/tracing.py` | Optional OpenTelemetry hooks |
| Errors | `src/core/exceptions.py` | `WandrError` tree → global handlers in `main.py` |
| Envelope | `src/core/responses.py` | Consistent JSON success/error shape |
| Pagination | `src/core/pagination.py` | Shared page params / responses |
| JWT / deps | `src/core/security/*` | Tokens + `require_auth` / `optional_auth` |
| DB | `src/core/database/*` | Engine, session, mixins, `BaseRepository` |

---

## Geo gateway layer

External map providers are **unstable and rate-limited**. All Nominatim / Overpass / OSRM traffic stays in `src/geo/`:

| File | Status | Public entry | Failure behavior |
|------|--------|--------------|------------------|
| `geo/schemas.py` | Real | DTOs: `GeocodedPlace`, `RawPOI`, `RouteResult` | — |
| `geo/geocoder.py` | Real | `geocode(query)` | returns `None` |
| `geo/overpass.py` | Real | `fetch_pois(lat, lng, radius_km)` | returns `[]` |
| `geo/osrm.py` | Real | `get_route(waypoints)` | haversine × 1.4 fallback; never raises httpx |

**Why a gateway?** Callers never build OverpassQL or Nominatim URLs. Resilience (timeouts, tenacity, fallbacks) lives in one place. See `openspec/specs/geo-geocoder/`, `geo-overpass/`, and `geo-osrm/`.

---

## AI / LLM boundary (critical)

```text
❌  Anywhere else importing litellm / groq / openai
✅  src/core/llm/client.py  →  chat_completion / chat_with_tools
```

**Product rule (even before planner ships):**

- LLM may help with **narrative / language**.  
- LLM must **not** invent place IDs, coordinates, stop order, or clock times — those come from DB, geo, and (later) `travel_engine` + tools.

Today the LLM client exists; the **planner LangGraph loop is still a stub**. Don’t assume agent tools are wired.

---

## Deterministic vs LLM (future)

| Kind of work | Where | I/O? |
|--------------|-------|------|
| Ranking days, travel times, validation | Future `travel_engine/` | **No** network/DB/LLM — pure Python; routing times injected |
| Tool side effects (search, route, persist) | Future `planner/tools/` + domain services | Yes, via gateways/services |
| Prose for the itinerary | LLM via `core/llm` **outside** the tool loop | Yes |

---

## App factory

`src/main.py` owns:

1. Lifespan (logging config, DB ping, tracer flush)  
2. Middleware registration  
3. Global exception handlers → `ErrorResponse`  
4. Router includes (`auth`, `destinations`, `places`)  
5. `GET /api/v1/health`

Next: [03 — Module map](03-module-map.md)
