## Why

P2.4 seeded Darjeeling into Postgres and DestinationService already does cache-aside search, but there is still no HTTP surface for destinations and no OSRM routing gateway. Steps **2.5** + **2.6c** (`docs/steps/step2.md`) are the next canonical pair: unlock `get_route()` for later planner/travel_engine work, and expose `GET /api/v1/destinations/search` so we can validate and **view live JSON in the browser** (Swagger + direct URL).

## What Changes

- Replace stub `src/geo/osrm.py` with OSRM driving-route gateway + haversine × 1.4 fallback (`RouteResult` already exists)
- Replace stub `src/destinations/router.py` with public search (+ readiness route stub pending 2.8) and register it in `src/main.py`
- Validate OSRM with scripted happy/failure paths; validate destinations API via curl, pytest-free live checks, **OpenAPI/Swagger UI in browser**, and direct browser hits to search JSON
- Update `docs/context.md` (2.5 + 2.6c ✅, Next → **2.6c′**)

**Step readiness:** Both steps are implementable now — `OSRM_BASE_URL` and `RouteResult` exist; `DestinationService.search` / `get_by_id` exist. Readiness **scoring** stays 2.8; this change only wires the route with a thin stub so registration matches the step doc without inventing 2.8 math.

## Capabilities

### New Capabilities

- `geo-osrm`: OSRM routing gateway with haversine fallback (never raises httpx to callers)
- `destinations-http`: Public destinations HTTP routes (`/search`; readiness route stub until 2.8)

### Modified Capabilities

- *(none)* — `destinations-core` service/repo requirements unchanged; this only adds the HTTP layer

## Impact

- **Code:** `src/geo/osrm.py`, `src/destinations/router.py`, `src/main.py` (router include); optional thin `get_readiness` stub on `DestinationService`
- **Live endpoints:** `GET /api/v1/destinations/search?q=…`; `GET /api/v1/destinations/{id}/readiness` (stub until 2.8)
- **Browser proof:** uvicorn → open `http://localhost:8000/docs` and search URL in browser
- **Deps:** none new — httpx + tenacity already present; `OSRM_BASE_URL` already on Settings
- **AGENT.md:** OSRM HTTP only in `src/geo/`; router → DestinationService only; no geocode import in router; `ApiResponse[T]` envelopes
- **Non-goals:** 2.6c′ path-specific rate limit; 2.7 places HTTP; 2.8 `compute_readiness`; 2.9 pytest modules; planner usage of OSRM
