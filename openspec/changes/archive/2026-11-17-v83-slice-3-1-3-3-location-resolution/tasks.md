## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.1–§6.3, §7.1–§7.2, and §9 rows 3.1–3.3, plus this change's `proposal.md`, `design.md`, and `specs/location-intelligence/spec.md`. There is no `docs/steps/step*.md` for these rows.
- [x] 1.2 Confirm writes stay inside `src/location_intelligence/**`, `src/config.py`, `.env.example`, `tests/location_intelligence/**`, `docs/context.md`, and the location rows of `docs/v8.2/repository_audit.md`. Do not edit `src/geo/geocoder.py`, `src/geo/schemas.py`, `src/destinations/**`, `src/planner/**`, `src/travel_engine/**`, `tests/travel_engine/test_properties.py`, `requirements.txt`, or `docs/FE_guide.md`.

## 2. Settings

- [x] 2.1 Add `LOCATION_V2_ENABLED` (default `false`), `LOCATION_AUTO_RESOLVE_CONFIDENCE` (`0.90`), `LOCATION_POI_RADIUS_KM` (`10`), `LOCATION_NEIGHBORHOOD_RADIUS_KM` (`5`), `LOCATION_CITY_FALLBACK_RADIUS_KM` (`15`), and `LOCATION_MAX_RADIUS_KM` (`50`) to `Settings` in `src/config.py`. Comment that the flag is unread until row 3.4. Read them only through `get_settings()`.
- [x] 2.2 Document the same six names and defaults in `.env.example`.

## 3. Pure library

- [x] 3.1 Add `src/location_intelligence/schemas.py` with `LocationType`, `CatalogHit`, `ResolvedLocation`, `LocationResolution`, and `SearchArea` as in the spec. Bounding box order is `[west, south, east, north]`. `CatalogHit` is a plain model, not a SQLAlchemy row.
- [x] 3.2 Add `confidence.py` and the classification rules in `resolver.py`. First matching rule wins. Explanation names the rule. Confidence uses the spec priors, then `+0.05` for the same OSM id or `+0.04` for the same normalized name within 1 km (haversine in this package), capped at `0.97`.
- [x] 3.3 Merge geocoder hits and catalog rows in `resolver.py`: cap 10, collapse the same `osm_place_id`, otherwise collapse the same normalized name within 1 km. Provider `nominatim` when an OSM id exists, `catalog` when the row is catalog-only. Order by confidence descending, then canonical name ascending.
- [x] 3.4 Resolve in `resolver.py`: `resolved` only when exactly one candidate is at or above the supplied threshold; otherwise `ambiguous` with `selected` null and `requires_confirmation` true when any candidate remains; `not_found` when the lists are empty. Do not substitute a city.
- [x] 3.5 Add `search_area.py`. Implement the spec's city, neighborhood, landmark, POI, address, map-pin, and polygon cases. City bbox becomes a closed rectangle ring. Address uses the neighborhood radius and says so. Clamp a map pin above `LOCATION_MAX_RADIUS_KM` without setting `fallback_used`. Raise a typed oversized-admin error for `country` and `region`. Raise a typed invalid-polygon error for a bad GeoJSON value. Do not add shapely.

## 4. Facade

- [x] 4.1 Add `service.py` with injectable geocoder and catalog ports. The default geocoder port calls `geocode_search` inside `asyncio.wait_for` using `SEARCH_GEOCODE_TIMEOUT_SECONDS`. Timeout returns `not_found` with reason `geocoder_timeout`. `ExternalServiceError` propagates. Do not add another retry loop.
- [x] 4.2 The default catalog port calls `DestinationRepository.search_by_name` and maps rows to `CatalogHit`. It does not commit and does not call `upsert_from_geocoded`. The facade builds the radius policy from `get_settings()` and passes it into the pure functions.

## 5. Tests

- [x] 5.1 Add `tests/location_intelligence/` covering the spec scenarios: settings defaults, Darjeeling city, Tiger Hill landmark, Ghoom Monastery POI, identical fixture twice, OSM-id collapse, no upsert, one city auto-resolves, one landmark stays ambiguous, two cities stay ambiguous, empty input is `not_found`, timeout is `geocoder_timeout`, 403/429 propagates, city boundary versus landmark radius, city fallback 15 km with `fallback_used`, map-pin clamp 80→50, country and region refuse, closed polygon accepted, open ring rejected.
- [x] 5.2 Add a scan test that fails if any file under `src/planner/` or `src/travel_engine/` contains `LOCATION_V2_ENABLED` or imports `src.location_intelligence`. Assert `tests/travel_engine/test_properties.py::test_area_respect` is still skipped.

## 6. Verify and completion sync

- [x] 6.1 Run `pytest tests/location_intelligence -v` and `pytest tests/architecture -v`. Both exit 0. Architecture stays green because the new flag defaults to false.
- [x] 6.2 Update `docs/context.md`: rows 3.1–3.3 are a dark library, generate is unchanged, and the next blueprint feature row is 3.4. Update `docs/v8.2/repository_audit.md` so `location_intelligence/` is implemented-tested with file, symbol, and test links, and the six settings are present and unread by the planner. Do not mark the Slice 3 exit gate done.
- [x] 6.3 Confirm the diff is only the paths in task 1.2. No HTTP route, no Alembic revision, no `requirements.txt` edit, and no change to destination search or resolve. Put the blueprint §19 completion report in the PR description.
