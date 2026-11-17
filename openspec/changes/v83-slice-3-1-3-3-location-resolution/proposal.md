## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **3.1**, **3.2**, and **3.3**, with contracts in §6.1–§6.3) is the next feature slice after Slice 2. There is no `docs/steps/step*.md` for these rows. `docs/context.md` names Slice 3 as the next blueprint feature slice. Rows 3.1–3.3 build the location model the later planner hook (3.4) will call. They do not change generate.

Today `DestinationService.search` and `resolve` already call `src/geo/geocoder.py` and the `destinations` catalog, then upsert a destination and return `destination` | `hubs` | `ambiguous`. That HTTP contract has no location type, no confidence, no `requires_confirmation` rule, and no search-area object. `src/location_intelligence/` is absent (`docs/v8.2/repository_audit.md`). `LOCATION_V2_ENABLED` is not on `Settings`. `tests/travel_engine/test_properties.py::test_area_respect` is still skipped because `SearchArea` does not exist.

## What Changes

- Add `src/location_intelligence/` as a deterministic library: candidate search, classification, resolution, and search-area construction.
- Reuse `geocode_search` and read-only catalog hits. Do not add a geocoding provider. Do not upsert destinations from this package.
- Map existing `GeocodedPlace` fields (`addresstype`, `osm_class`, `osm_type_tag`, bbox, `display_name`) onto §6.1 types. Confidence is a documented prior plus a catalog bump, because `GeocodedPlace` has no Nominatim `importance` and this change does not edit the geocoder.
- Auto-resolve only when exactly one candidate is at or above `LOCATION_AUTO_RESOLVE_CONFIDENCE`. Otherwise return the candidates and require confirmation. An empty result is `not_found`, never a substituted city.
- Build a `SearchArea` per §6.3: city and neighborhood boundaries when a bbox exists, disclosed radius fallback when it does not, point radii for landmark, POI, and address, clamped map-pin radius, validated GeoJSON polygon. Country and region do not receive a hidden radius.
- Add the §7.2 location settings and `LOCATION_V2_ENABLED`, all defaulting to the blueprint values. Nothing in the planner or `travel_engine` reads them in this change.
- No **BREAKING** HTTP, SSE, or persisted-trip change.

## Capabilities

### New Capabilities

- `location-intelligence`: candidate search, type classification, resolution, and search-area construction behind settings that default to the legacy values and are not consulted by generate.

### Modified Capabilities

- None. `destinations-http` and `geo-geocoder` keep their current requirements. `GET /api/v1/destinations/search` and `GET /api/v1/destinations/resolve` stay as they are.

## Impact

- **Work surface:** `src/location_intelligence/**`, additive fields only if a schema in `src/geo/schemas.py` must grow (this change does not plan to grow it), `src/config.py`, `.env.example`, `tests/location_intelligence/**`.
- **Completion sync (outside the §9 path cell, requested for this change):** `docs/context.md` and the `location_intelligence/` plus location-settings rows in `docs/v8.2/repository_audit.md`, after the tests pass. No other doc.
- **No new package.** No `requirements.txt` change. No Alembic revision. No router.
- **External I/O:** only through the existing `geocode_search` (timeout, tenacity, and empty-list fallback already live there). This package adds `asyncio.wait_for` with `SEARCH_GEOCODE_TIMEOUT_SECONDS`. A timeout becomes `not_found`. `ExternalServiceError` from Nominatim 403/429 still propagates and is not stored as `not_found`.
- **No impact on:** planner generate, SSE event names, trip columns, retrieval radius, `DestinationService`, or the skipped `test_area_respect` (retrieval inside a search area is row 3.4).

## Non-goals

- No planner integration, no retrieval filter, and no `discovery_anchor` / `search_area` column (row 3.4).
- No `locations/search`, `locations/resolve`, or `locations/search-area` routes, and no `docs/FE_guide.md` edit (rows 3.5 and 3.6). Frontend agreement is still open.
- No change to `DestinationService.search` or `resolve`, including their upsert-on-miss behavior.
- No edit to `src/geo/geocoder.py`. No second Nominatim client. No new provider.
- No un-skip of `test_area_respect` and no `travel_engine` edit. The engine still does not import `SearchArea`.
- No Slice 4–9 work, no lodging, no media, no judge, no golden-suite expansion. §11.2's open case-count gap stays with Slice 2; these rows do not change ranking, location-in-generate, or engine behavior, so N1 does not block a dark library.
- No rewrite of §9 in the blueprint. Checkout corrections are recorded in this change, not patched into the blueprint.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep Nominatim HTTP inside `src/geo/geocoder.py`. `location_intelligence` calls `geocode_search` and does not open a URL.
- Read every new knob through `get_settings()`. No `os.environ`.
- Leave `travel_engine/` free of I/O and free of this package.
- Leave routers on the service layer. This change adds no router.
- Add no LLM call and no provider SDK import.
- Keep `LOCATION_V2_ENABLED` default false. Generate stays on the current destination and base path (N2's switch exists here; row 3.4 is what it will gate).
- Treat a missing boundary, price, or hour as unknown or disclosed. This slice discloses radius fallback. It does not invent "open".

Blueprint path notes, confirmed against the checkout rather than treated as a halt:

- `src/config.py` and `.env.example` are outside the row's path cell. The radii and the flag cannot live anywhere else, because env access is only legal in settings. This is the same kind of one-file wiring 2.1 used for `scripts/run_evals.py`.
- Tests live in `tests/location_intelligence/**` because the verify command is `pytest tests/location_intelligence -v`.
- `docs/context.md` and `docs/v8.2/repository_audit.md` are updated only as the feature-completion sync. They do not describe generate as location-aware.
