## 1. Overpass gateway

- [x] 1.1 Replace stub `src/geo/overpass.py` with Overpass gateway per step 2.2 + design: locked OverpassQL template, `_category_from_tags`, `_element_to_poi` (skip unnamed / missing coords), `_post_overpass` (form `data=`, timeouts connect=10/read=30, tenacity 3× wait 2–16s on Timeout/Connect only, 4xx → `{"elements": []}`, User-Agent from `NOMINATIM_USER_AGENT`), `fetch_pois` (build query, parse, dedupe by `osm_id` last-wins, try/except → `[]`) — no SQLAlchemy/FastAPI/DB imports; URL via `get_settings().OVERPASS_API_URL`
- [x] 1.2 Confirm `fetch_pois` never raises httpx exceptions to callers and does not widen OverpassQL beyond the locked template

## 2. CLI script

- [x] 2.1 Create `scripts/test_overpass.py` — `python scripts/test_overpass.py <lat> <lng> <radius_km>` with defaults `27.041 88.263 30`; print `Fetched {n} POIs` and first 3 POI names

## 3. Validation (step 2.2)

- [x] 3.1 Live scrape: `python scripts/test_overpass.py 27.041 88.263 30` → `Fetched {n} POIs` with `n >= 50` (blueprint cites ~144)
- [x] 3.2 Failure path: mock `_post_overpass` with `httpx.ConnectError` → `fetch_pois` returns `[]` (step 2.2 inline snippet)

## 4. Context checkpoint

- [x] 4.1 Update `docs/context.md` — mark 2.2 ✅, Next step **2.3**, add `geo/overpass` to Implemented modules, remove it from stubs list
