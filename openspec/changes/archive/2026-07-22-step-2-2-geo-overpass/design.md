## Context

P2.1 is done: `GeocodedPlace` / `RawPOI` / `RouteResult`, Nominatim gateway, `OVERPASS_API_URL` in config. `src/geo/overpass.py` is still a one-line stub. Canonical order is 2.1 → **2.2** → 2.3 (`docs/steps/step2.md`). AGENT.md: all Overpass I/O only inside `src/geo/`. Blueprint resilience: Overpass → tenacity 3× (wait 2–16s) → return `[]` → seed continues.

## Goals / Non-Goals

**Goals:**
- Real Overpass gateway: `fetch_pois(lat, lng, radius_km) -> list[RawPOI]`
- Encapsulated OverpassQL (callers never build queries)
- Locked category mapping, unnamed skip, `osm_id` dedupe (last wins)
- Explicit httpx timeouts + tenacity (connect/timeout only); failures → `[]`
- CLI `scripts/test_overpass.py` + step 2.2 validation paths
- Update `docs/context.md` after validation (2.2 ✅, Next → 2.3)

**Non-Goals:**
- Config/schema changes (`OVERPASS_API_URL`, `RawPOI` already in 2.1)
- Place repository (2.3), seed script (2.4), OSRM (2.5), destinations/places routers
- Caching Overpass responses
- Pytest module `tests/geo/test_overpass.py` (step 2.9) — 2.2 uses script + inline failure mock
- New package installs
- Expanding OverpassQL beyond the locked template (e.g. `way` for park/trailhead)

## Decisions

### D1 — Gateway isolation (match geocoder)
- `_post_overpass` owns URL, body, timeouts, 4xx handling; public API is only `fetch_pois`.
- No SQLAlchemy / FastAPI / DB imports in `geo/overpass.py`.
- Env only via `get_settings().OVERPASS_API_URL`.

### D2 — POST as form `data=` (Overpass interpreter contract)
- Step says “POST … with query body.” Overpass public interpreter expects `application/x-www-form-urlencoded` field `data=<OverpassQL>`.
- **Locked:** `client.post(url, data={"data": query})` — not raw JSON body.
- **Alt rejected:** JSON POST — not the interpreter’s documented API.

### D3 — Resilience contract (timeouts + retry)
- `_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)`
- **Amendment vs step/blueprint `read=30`:** client read MUST exceed OverpassQL `[timeout:60]` slack for slow public mirrors. `read=30` caused systematic `[]` on Darjeeling `radius_km=30`; `read=90` matched the successful probe that returned 95 elements.
- **Amendment vs step retry set:** also retry transient **5xx** (`HTTPStatusError` with `response.is_server_error`) — public Overpass frequently returns 504 under load.
- `@retry(..., retry=retry_if_exception(_is_retryable))` where `_is_retryable` covers TimeoutException, ConnectError, and 5xx HTTPStatusError
- 4xx → log warning, return `{"elements": []}` (no retry)
- `fetch_pois` MUST wrap `_post_overpass` in try/except for `httpx.TimeoutException`, `httpx.ConnectError`, and `httpx.HTTPError` → log + return `[]`

### D4 — Category mapping (priority order, locked P2 table)
Inspect tags in this order; first match wins; else `"attraction"`:
1. `tourism=museum` → `museum`
2. `tourism=viewpoint` → `viewpoint`
3. `tourism=monastery` → `monastery`
4. `tourism=attraction` → `attraction`
5. `leisure=park` → `park`
6. `highway=trailhead` → `trailhead`
7. fallback → `attraction`

### D5 — Element parsing
- Skip if no `tags.name` (unnamed discarded)
- Coords: `element["lat"]`/`["lon"]`, else `element["center"]["lat"]`/`["lon"]` for ways; skip if neither
- `osm_id = f"{element['type']}/{element['id']}"`
- `raw_tags` = shallow copy of tags dict
- Deduplicate with `dict[osm_id] = poi` (iteration order → last wins), then `list(values)`

### D6 — OverpassQL template (do not widen)
Use the exact template from step 2.2 (`radius_m = int(radius_km * 1000)`): tourism node+way regex; park and trailhead **nodes only**. Do not add ways for park/trailhead in this step.

### D7 — User-Agent without new config
- Step does not require a dedicated Overpass UA. Send `User-Agent: settings.NOMINATIM_USER_AGENT` so public Overpass can identify the client (same app identity as Nominatim). No new env var.

### D8 — No Overpass cache in P2.2
- Seed/scrape is infrequent vs geocode; no process dict cache. Defer any cache if a later step needs it.

## Risks / Trade-offs

- [Public Overpass flaky / rate limits] → tenacity 3× + `[]` fallback; seed (2.4) continues with `place_count=0`
- [Client read=30s vs QL timeout=60s] → Accept step lock; retries may help on slow responses
- [POI count varies over time] → Validation expects `n >= 50` for Darjeeling (~144 cited); not a fixed constant
- [Live validation needs network] → Failure path uses mock; live CLI optional when offline
- [Duplicate OSM elements across node/way] → Dedupe by `osm_id` last-wins

## Migration Plan

1. Implement `src/geo/overpass.py` (replace stub)
2. Add `scripts/test_overpass.py`
3. Run step 2.2 validation (live + failure mock)
4. Update `docs/context.md` (2.2 ✅, Next → 2.3, implemented modules, stubs)
5. Rollback: revert those two files; no DB/migration impact

## Open Questions

- None blocking for 2.2. (Resolved in design: form `data=` POST, User-Agent reuse, outer catch on `fetch_pois`, no query widening.)
