## Context

P2.4 + 2.6b are done: seed loads Darjeeling; `DestinationService.search` works in-process. `src/geo/osrm.py` and `src/destinations/router.py` are still step-0.1 stubs. Canonical next pair from `docs/steps/step2.md`: **2.5** (OSRM gateway) then **2.6c** (destinations HTTP). Operator wants live proof in the **browser** (Swagger + JSON URL), not only curl.

## Goals / Non-Goals

**Goals:**
- `get_route(waypoints)` → `RouteResult` via OSRM, with haversine × 1.4 fallback (never raises httpx)
- `GET /api/v1/destinations/search` → `ApiResponse[list[DestinationOut]]` via DestinationService only
- Register destinations router in `main.py`; show results in browser (`/docs` + search URL)
- Per-step validation gates in tasks (2.5 scripts first, then 2.6c HTTP/browser)
- Update `docs/context.md` → Next **2.6c′**

**Non-Goals:**
- 2.6c′ destinations-search rate limit (20/min)
- 2.8 `compute_readiness` formula (full readiness math)
- Places HTTP (2.7), pytest suite (2.9), planner calling OSRM
- New packages or config fields (`OSRM_BASE_URL` already exists)

## Decisions

### D1 — Match geocoder/overpass gateway pattern for OSRM
- Explicit `httpx.Timeout(connect=5, read=10, write=10, pool=5)`; tenacity **2** attempts, `wait_fixed(1)`, retry only Timeout/ConnectError
- Base URL from `get_settings().OSRM_BASE_URL`
- Public API: `get_route`; private `_call_osrm` / `_fallback_route` / `_haversine_km`
- Alternative considered: raise on OSRM failure — rejected (blueprint named fallback)

### D2 — Waypoint contract
- Input: `list[tuple[lat, lng]]`, `len >= 2` else `ValueError`
- OSRM URL uses `lng,lat` order: `/route/v1/driving/{lng},{lat};...`
- Map meters→km, seconds→minutes; `geometry` → `encoded_polyline`; empty/failed → fallback

### D3 — Fallback math (locked)
- Sum haversine legs × `_HAVERSINE_ROAD_FACTOR` (1.4)
- `duration_min = distance_km / _AVG_SPEED_KMH * 60`
- `fallback_used=True`; log warning; `distance_km > 0` when waypoints differ

### D4 — Router → Service only
- Search: `DestinationService(db).search(q)` → `DestinationOut.model_validate`
- No auth on search (public catalog)
- Must NOT import `geocode` / SQLAlchemy models in router beyond typing if needed
- Alternative: call repository from router — rejected (AGENT.md)

### D5 — Readiness route stub until 2.8
- Register `GET /{destination_id}/readiness` as in the step doc
- Add thin `DestinationService.get_readiness`: load dest or `DestinationNotFoundError`; if found, return `DestinationReadinessOut` with `place_count` from dest, `score=0.0`, `tier="sparse"`, pcts `0.0`, message that full scoring lands in **2.8**
- Alternative: omit route until 2.8 — rejected (breaks step 2.6c registration); Alternative: implement full formula now — rejected (scope of 2.8)

### D6 — Browser + API validation is a first-class gate
- Start `uvicorn src.main:app --reload --port 8000`
- Open `http://localhost:8000/docs` — Try it out on `/api/v1/destinations/search`
- Open `http://localhost:8000/api/v1/destinations/search?q=Darjeeling` in browser (raw JSON)
- Also curl + nonsense-q → 404 for automation
- OSRM has no HTTP route in this change — validated via `python -c` only

### D7 — Combined change, separate validation sections
- Tasks grouped: §1 OSRM implement+validate → §2 router implement → §3 HTTP/browser validate → §4 context
- Do not mark 2.6c done until browser/search proof passes

## Risks / Trade-offs

- [Public OSRM slow/down] → fallback still returns usable RouteResult; assert `distance_km > 0`
- [Readiness stub confuses operators] → message field + context.md marks 2.8 next for scoring
- [Nominatim on cold search miss] → expected; Darjeeling already seeded so search should DB-hit
- [Browser CORS] → same-origin Swagger/docs and direct GET are fine; no SPA yet
- [PYTHONPATH shadowing other projects] → tasks note `PYTHONPATH=repo root` on Windows

## Migration Plan

1. Implement `src/geo/osrm.py`; run 2.5 validations
2. Implement router + readiness stub + `main.py` include
3. Start uvicorn; curl + browser + Swagger proof
4. Update `docs/context.md` (2.5, 2.6c ✅; Next 2.6c′; Live endpoints)
5. No Alembic

## Open Questions

- None blocking. Readiness stub content is an explicit interim until 2.8.
