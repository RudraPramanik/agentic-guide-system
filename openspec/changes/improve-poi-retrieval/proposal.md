## Why

Planner candidates come almost entirely from a narrow Overpass scrape (tourism attraction/viewpoint/museum/monastery + park + trailhead). That misses cafes, food, worship, historic, and nature POIs, and has no popularity signal—so itineraries feel sparse or “not the best options” even when `place_count` clears the floor. We need better retrieval into the existing PostGIS → enrich → Qdrant → planner path without replacing Nominatim/OSRM or breaking prepare/seed contracts.

## What Changes

- Widen the OverpassQL tag set and category mapping so food, worship, historic, and nature POIs enter `RawPOI` / `Place` through the same gateway.
- Introduce a geo-layer **places provider** abstraction that always emits `list[RawPOI]`; keep `Place.osm_id` as the unique external id (prefix non-OSM ids, e.g. `otm:…`).
- Add **OpenTripMap** as an optional secondary provider (tourism + rate/popularity) behind a settings flag; merge + dedupe before upsert.
- Optionally wire **Geoapify Places** the same way (feature-flagged); default off until benchmarked.
- Extend structural visit durations for new categories (`cafe`, `restaurant`, `temple`, `historic`, `nature`) used by `travel_engine`.
- Update prepare/seed ingest to call the provider facade (not Overpass-only), still via `src/geo/` only.
- **No BREAKING** HTTP/DTO changes: destinations prepare, places list/get, planner generate contracts stay the same.

### Non-goals

- Replacing Nominatim or changing routing (`haversine` / OSRM).
- Overture / FSQ OS Places ETL dumps (spike later, out of this change).
- Google Places, live Foursquare API, or Mapbox as required deps.
- Rewriting `rank_places` / LLM preference parsing (may consume `raw_tags` popularity later in a follow-up).
- Schema rename of `osm_id` column.

## Capabilities

### New Capabilities

- `places-provider`: Settings-driven multi-source POI fetch facade under `src/geo/` that returns normalized `RawPOI` lists (Overpass always; OpenTripMap / Geoapify optional), with id prefixing and cross-source dedupe before callers upsert.

### Modified Capabilities

- `geo-overpass`: Broader OverpassQL + category mapping beyond the locked P2 six-tag set; still fail-soft to `[]`.
- `destination-prepare`: Prepare ingest uses the places-provider facade (not Overpass-only); HTTP 200/202/floor behavior unchanged.
- `seed-destination`: CLI seed uses the same facade; geocode / empty / per-POI failure boundaries unchanged.
- `travel-engine-rules`: Structural `VISIT_DURATION_BY_CATEGORY` gains new P2+ categories introduced by retrieval.

## Impact

| Area | Effect |
|------|--------|
| `src/geo/overpass.py` | Wider query + category map |
| `src/geo/` (new modules) | Provider protocol, OpenTripMap client, optional Geoapify, composite merge |
| `src/destinations/ingest.py` | Call facade instead of `fetch_pois` only |
| `src/config.py` / `.env.example` | `PLACES_SOURCES`, OpenTripMap + Geoapify settings |
| `src/travel_engine/travel_rules.py` | New category durations |
| Tests | Overpass category/query unit tests; provider merge/dedupe; prepare/seed still green |
| HTTP / FE | No new endpoints; richer place catalogs after re-prepare |

### API keys required?

| Source | API key? | Notes |
|--------|----------|--------|
| **Overpass (widened)** | **No** | Uses existing `OVERPASS_API_URL` / public mirrors |
| **Nominatim / OSRM** | **No** | Unchanged |
| **OpenTripMap** | **Yes** (free signup) | Required only if `opentripmap` is in `PLACES_SOURCES`. Free tier ~5k req/day, **non-commercial**. Set `OPENTRIPMAP_API_KEY` |
| **Geoapify Places** | **Yes** (free signup) | Required only if `geoapify` is in `PLACES_SOURCES`. Free ~3k credits/day + attribution. Set `GEOAPIFY_API_KEY` |

**Default for this change:** `PLACES_SOURCES=overpass` (no new keys). Enabling OpenTripMap (recommended secondary) needs one free key. Geoapify remains optional/off by default.
