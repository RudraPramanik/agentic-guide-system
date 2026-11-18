## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.2–§6.3, §8.1, §9 rows 3.4–3.6, and §11.3–§11.4, plus this change's `proposal.md`, `design.md`, and the delta specs. There is no `docs/steps/step*.md` for these rows.
- [x] 1.2 **guideagent.** Keep production edits to the paths in the proposal Impact list. Do not edit `src/geo/geocoder.py`, `src/travel_engine/**` (except the skipped property test under `tests/travel_engine/`), `requirements.txt`, destination search/resolve behavior, or SSE event names. Do not redefine `base_lat`/`base_lng`.
- [x] 1.3 **guideagent-frontend.** Do not implement the compose panel in this backend PR. That work is the sibling change `v83-slice-3-6-location-picker`. This PR only writes the contract in `docs/FE_guide.md` and `docs/blueprint_frontend.md`.

## 2. Columns and trip JSON

- [x] 2.1 **guideagent.** Add nullable JSONB `discovery_anchor` and `search_area` on `Trip` and one Alembic revision. No backfill, no other column change. Downgrade drops only those columns.
- [x] 2.2 **guideagent.** `save_from_state` keeps `base_lat`/`base_lng` in `preferences` and writes the two columns only when state carries a server-built anchor and area. It does not copy the anchor into the base.
- [x] 2.3 **guideagent.** `TripOut` omits `discovery_anchor` and `search_area` when they are null and still emits other null fields as it does today. `_resolve_base` does not read the anchor.

## 3. Containment and retrieval

- [x] 3.1 **guideagent.** Add a pure containment function in `src/location_intelligence/` (haversine for radius, ray cast for rings). No shapely. Map pins built by the server use provider `user` and do not enter candidate merge.
- [x] 3.2 **guideagent.** Add a filter helper in `src/search/places_index.py` that subsets loaded places. Do not change the `search_places()` signature or the Qdrant query.
- [x] 3.3 **guideagent.** In the DISCOVER `search_places` tool, when state has no search area, keep the trip base and `SEARCH_DEFAULT_RADIUS_KM`. When state has an area, drop places outside it, and point the PostGIS fallback at the anchor and that area (covering radius from the ring bbox, then the predicate). Do not pass 30 on that branch. Keep `fusion_diagnostics` when the search layer produced them.
- [x] 3.4 **guideagent.** Replace the skip on `tests/travel_engine/test_properties.py::test_area_respect` with assertions on the pure predicate. `src/travel_engine/**` still must not import `src.location_intelligence`. Update the isolation scan so the planner may import the package and the engine may not.

## 4. Generate flag branch

- [x] 4.1 **guideagent.** Add optional `discovery_anchor` and `radius_km` to `PlanRequest`. A body without them still validates. The anchor must not overwrite `base_lat`/`base_lng`.
- [x] 4.2 **guideagent.** Add a read-only destination-center mapper on `DestinationService`. It does not commit and does not call `search` or `resolve`.
- [x] 4.3 **guideagent.** In the generate router, when the flag is false, ignore the new fields, pass an empty location suffix, and do not call the location library. Idempotency material and the preference-cache key stay the current strings.
- [x] 4.4 **guideagent.** When the flag is true, build one server-owned area before the graph (destination-center fallback, map pin, or confirmed candidate) per the spec. Fail 422 `anchor_not_confirmed`, `oversized_admin`, or `invalid_coordinates` before the graph. Put dicts on travel state. Include the anchor and radius in the idempotency suffix and the cache key only when the body sent them. Do not add a field to `itinerary_done`.
- [x] 4.5 **guideagent.** Give `request_material` an optional suffix that defaults to empty so existing callers stay byte-identical.

## 5. Location routes

- [x] 5.1 **guideagent.** Add `src/location_intelligence/router.py` with `POST /api/v1/locations/search`, `/resolve`, and `/search-area`, and include it from `src/main.py`. Flag off returns 404 before the geocoder. Success is `ApiResponse`. No destination upsert. Resolve confirms only the posted provider id.
- [x] 5.2 **guideagent.** Add the three path settings, defaulting to those URLs, and document them in `.env.example`. The rate-limit table uses the existing destinations-search 20/60 budget for each path. No new numeric budget.
- [x] 5.3 **guideagent.** Map `oversized_admin`, `invalid_polygon`, and `invalid_coordinates` to HTTP 422. Let Nominatim 403/429 propagate as the existing external-service error.

## 6. Location suite

- [x] 6.1 **guideagent.** Add `evals/golden/location/*.json` fixtures for Darjeeling as a city, Tiger Hill as a landmark, an ambiguous pair, a map pin that clamps 80 km to 50 km, and a stop outside a radius. Do not put these files in `evals/golden/darjeeling/` and do not add assertion keys to the itinerary loader.
- [x] 6.2 **guideagent.** Add `--suite location` to `scripts/run_evals.py`. It scores that folder with the pure resolver, builder, and containment predicate, does not call `PlannerService` or the network, and treats `--replay` as a no-op. Omitting `--suite` still loads Darjeeling only.

## 7. Contract docs

- [x] 7.1 **guideagent.** Update `docs/FE_guide.md` and `docs/blueprint_frontend.md` with the three routes, the optional generate fields, the 404-when-flag-off rule, the anchor-versus-base rule, and the compose-page panel. State that home and explore still use `GET /api/v1/destinations/resolve` to obtain `destination_id`.

## 8. Proof and completion sync

- [x] 8.1 **guideagent.** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on an empty database, and upgrade against a database that already has trips, leaves those rows' other columns intact and the new columns null.
- [x] 8.2 **guideagent.** `pytest tests/location_intelligence tests/snapshots tests/planner tests/travel_engine/test_properties.py tests/architecture -v` exits 0. Flag-off snapshot bodies are unchanged. A flag-on fallback test shows the radius is not 30.
- [x] 8.3 **guideagent.** `python scripts/run_evals.py --replay --suite location` exits 0. `python scripts/run_evals.py --replay` without `--suite` still scores Darjeeling and does not read the location folder.
- [x] 8.4 **guideagent.** Update `docs/context.md`: rows 3.4–3.6 are implemented, the flag still defaults to false, generate uses a search area only when the flag is on, and the next blueprint row is Slice 4. Update the matching rows in `docs/v8.2/repository_audit.md` with file, symbol, and test links. Do not mark Slice 4 done.
- [x] 8.5 **guideagent.** Put the blueprint §19 subslice completion report in the backend PR description. The frontend PR is the sibling change, not this diff.
