## 1. Settings and Overpass widen

- [x] 1.1 Add `PLACES_SOURCES`, `OPENTRIPMAP_API_KEY`, `OPENTRIPMAP_BASE_URL`, `GEOAPIFY_API_KEY`, `GEOAPIFY_BASE_URL` to `src/config.py` via `get_settings()` with defaults (`PLACES_SOURCES=overpass`; keys empty; sane base URLs)
- [x] 1.2 Document new env vars and API-key requirements in `.env.example` (Overpass = no key; OpenTripMap/Geoapify = free keys only when enabled)
- [x] 1.3 Widen OverpassQL in `src/geo/overpass.py` for cafe/restaurant, place_of_worship, historic, natural peak/waterfall while keeping existing tourism/park/trailhead selectors
- [x] 1.4 Extend `_category_from_tags` for `cafe`, `restaurant`, `temple`, `historic`, `nature` with priority order matching the geo-overpass delta spec
- [x] 1.5 Update Overpass unit tests for new category mapping and query selectors (mocked HTTP; no live Overpass required in CI)

## 2. Places provider facade

- [x] 2.1 Add `fetch_destination_pois(lat, lng, radius_km) -> list[RawPOI]` facade under `src/geo/` that reads `PLACES_SOURCES` and unions enabled sources
- [x] 2.2 Implement Overpass path as calling existing `fetch_pois` when `overpass` is enabled
- [x] 2.3 Implement OpenTripMap client (httpx + timeouts/retry; map to `RawPOI` with `otm:` ids; store rate/kinds in `raw_tags`); skip + warn if key empty
- [x] 2.4 Implement Geoapify Places client (same fail-soft pattern; `geoapify:` ids); skip + warn if key empty; may ship behind flag even if default-off
- [x] 2.5 Implement cross-source dedupe (exact `osm_id`, then ~75 m + normalized name; prefer OSM on collision)
- [x] 2.6 Unit-test facade: default overpass-only; missing optional key skips; one source failure keeps sibling results; dedupe prefers OSM

## 3. Ingest + travel rules wiring

- [x] 3.1 Switch `src/destinations/ingest.py` (prepare + seed path) from direct `fetch_pois` to `fetch_destination_pois`
- [x] 3.2 Confirm `scripts/seed_destination.py` still goes through ingest/geo only (no direct httpx/Overpass)
- [x] 3.3 Extend `VISIT_DURATION_BY_CATEGORY` in `travel_rules.py` for `cafe`, `restaurant`, `temple`, `historic`, `nature`
- [x] 3.4 Update travel_rules / related unit tests for new duration keys

## 4. Verification

- [x] 4.1 Run targeted pytest for geo/overpass, places-provider, travel_rules, destinations prepare/seed tests
- [x] 4.2 Manual or scripted check with `PLACES_SOURCES=overpass` only (no new keys): re-prepare a known destination and confirm new categories appear
- [x] 4.3 Optional live check: set `OPENTRIPMAP_API_KEY`, `PLACES_SOURCES=overpass,opentripmap`, re-prepare, confirm `otm:` rows and no duplicate near-matches vs OSM
- [x] 4.4 Update `docs/context.md` Implemented modules / geo notes after validation (no full manual rewrite)
