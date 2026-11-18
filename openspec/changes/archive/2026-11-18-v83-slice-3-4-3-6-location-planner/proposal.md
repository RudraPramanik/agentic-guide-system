## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **3.4**, **3.5**, and **3.6**, with §6.2–§6.3 and §11.3–§11.4) is the next feature slice. There is no `docs/steps/step*.md` for these rows. `docs/context.md` names 3.4 as the next blueprint row. Rows 3.1–3.3 shipped a dark library. Generate still ignores it: Qdrant is destination-scoped only, and the PostGIS fallback uses `SEARCH_DEFAULT_RADIUS_KM` (30) around `base_lat`/`base_lng`. `Trip` has no `discovery_anchor` or `search_area`. `GET /api/v1/destinations/search` and `GET /api/v1/destinations/resolve` stay the catalog intake. They do not return a location type, a confidence, `requires_confirmation`, or a `SearchArea`. That is the S0 gap for row 3.5.

This request assigns the frontend owner and agrees the contract below, which clears the row 3.5 stop (“FE contract not agreed”) and the row 3.6 stop (“no FE owner”). The flag stays default false, so legacy clients stay on the current path until an operator turns it on.

## What Changes

- When `LOCATION_V2_ENABLED` is false, generate, retrieval, idempotency material, the preference cache key, and trip JSON stay as they are. `base_lat`/`base_lng` remain the trip base in both modes. They are not redefined.
- When the flag is true, map a legacy generate body (destination id, optional base) to an internal anchor and search area. The anchor is the destination center. The search area is the disclosed city fallback (`LOCATION_CITY_FALLBACK_RADIUS_KM`), because a `Destination` row has no bbox. Retrieval uses that area for Qdrant hits and for the PostGIS fallback. The constant 30 is not used on this path.
- Accept an optional discovery anchor on `PlanRequest`. The server rebuilds the area. It does not trust a client polygon. A map pin is a user point plus a clamped radius. A nominatim or catalog selection is confirmed against a fresh search. Country and region fail before the graph with the existing `oversized_admin` code. No hub substitution inside generate.
- Store `discovery_anchor` and `search_area` as nullable JSONB on `trips`. `TripOut` omits both keys when they are null, so flag-off trip payloads do not grow. `base_lat`/`base_lng` stay inside `preferences`.
- Add `POST /api/v1/locations/search`, `POST /api/v1/locations/resolve`, and `POST /api/v1/locations/search-area`. They return `ApiResponse` of the existing resolution and search-area models. They do not upsert destinations. They return 404 when the flag is false and do not call Nominatim in that case. They share the existing destinations-search rate budget (20 requests / 60 seconds / IP).
- Add a location golden suite that the default Darjeeling itinerary run does not load. `scripts/run_evals.py` gains `--suite location` because that flag is not on the script today. The suite scores type accuracy, ambiguity, and containment without an LLM call. `--replay` is accepted and does not call the provider.
- Write the frontend contract in `docs/FE_guide.md` and `docs/blueprint_frontend.md`. The compose page, after a destination is already chosen, gains a candidate list with type labels, a selected anchor, a radius control, a search-area preview, and an anchor-versus-base distinction. Home and explore keep `GET /api/v1/destinations/resolve` as the way to obtain `destination_id`. The UI work is a second pull request in `guideagent-frontend`, with its own OpenSpec change.
- No **BREAKING** change to existing routes, SSE event names, or flag-off payloads.

## Capabilities

### New Capabilities

- None. The HTTP surface extends `location-intelligence`. It does not introduce a second location model.

### Modified Capabilities

- `location-intelligence`: the planner may read the flag and call the library; `travel_engine` still must not. Add containment, a `user` provider for map pins, and the three routes gated by the flag.
- `planner-sse-generate`: optional anchor and radius on `PlanRequest`, ignored while the flag is false. Flag-on mapping, pre-stream `oversized_admin`, and unchanged SSE event names.
- `planner-discover-tools`: `search_places` keeps the 30 km fallback only when state has no search area. When an area is present, both Qdrant hits and the PostGIS fallback stay inside it.
- `trips-repository-service`: additive nullable columns. Base coordinates remain in `preferences`. Trip JSON omits the new keys when null.
- `database-migrations`: one additive Alembic revision for those columns, with downgrade.
- `eval-golden-harness`: a location suite beside the itinerary cases. The closed itinerary assertion set and the twelve Darjeeling files stay as they are.
- `rate-limit-middleware`: the three location paths use the existing destinations-search request budget.

## Impact

- **Work surface:** cross-boundary. Backend pull request in `guideagent`. Frontend pull request in `guideagent-frontend`. This is not a row in `docs/context/symptoms.md`. Guest-cookie and ownership rules there still apply to `GET /trips/{id}` when the new columns are present. Do not mix `localhost` and `127.0.0.1`.
- **Backend:** `src/planner/**`, `src/destinations/service.py` (a read-only mapper only), `src/search/places_index.py` (a filter helper only; `search_places()` stays destination-scoped), `src/trips/**`, `src/location_intelligence/router.py`, `src/main.py` (include the router), `src/config.py` and `.env.example` (three path settings only), `src/core/middleware/rate_limit.py`, `alembic/versions/`, `scripts/run_evals.py`, `evals/golden/location/**`, `tests/**` named by the verify commands.
- **Contract docs:** `docs/FE_guide.md`, `docs/blueprint_frontend.md`.
- **Completion sync:** `docs/context.md` and the location rows in `docs/v8.2/repository_audit.md` after the verify commands pass. The sibling frontend change updates its own spec. No other doc.
- **Frontend:** compose-page panel and generate body. Regenerate `types/generated/api.d.ts` from OpenAPI. Do not hand-edit it. Home resolve stays the primary destination intake.
- **No new package.** No `requirements.txt` change. No second geocoder. No Qdrant geo index. No change to `SEARCH_DEFAULT_RADIUS_KM` for the flag-off path. No change to `PLANNER_GENERATION_TIMEOUT_SECONDS`.

## Non-goals

- No change to `GET /api/v1/destinations/search`, `GET /api/v1/destinations/resolve`, or their upsert behavior.
- No upsert from `location_intelligence`. A landmark does not become a destination row.
- No edit to `src/geo/geocoder.py`. No new provider SDK.
- `travel_engine/` does not import this package and does not gain a search-area parameter. Containment happens before candidates enter the engine.
- No SSE event rename, no `run_id` change, and no new field on `itinerary_done`. The saved trip carries the area. The client reads it with `GET /trips/{id}`.
- No redefinition of `base_lat`/`base_lng`. A stop that would require that change stops the slice for an ADR.
- No Slice 4–9 work, no lodging, no media, no validator-v2 finding codes, no opening-hours claim.
- No attempt to close the §11.2 case-count gap (Manali, Goa, forty cases). The location suite is the location gate only.
- No rewrite of §9 in the blueprint. Checkout corrections stay in this change.
- The flag default stays false. Shipping the routes dark is the rollback. Removing the router remains the code rollback named in the blueprint.

## Constraints

From `AGENT.md` and the v8.3 invariants:

- Nominatim HTTP stays inside `src/geo/geocoder.py`. The new router calls `LocationIntelligenceService`.
- Routers stay on the service layer. The location router does not touch the database.
- New knobs go through `get_settings()`. No `os.environ`.
- Responses use `ApiResponse[T]`. SSE stays a raw event stream.
- `travel_engine/` stays free of I/O and of this package.
- No LLM call on the location routes or in the location suite.
- Flag-off generate is the N2 legacy path. Flag-on behavior is the switch row 3.4 exists to add.
- A missing boundary is a disclosed fallback. A country is not given a hidden radius.

Checkout notes, confirmed against the tree rather than treated as a halt:

- `scripts/run_evals.py` has no `--suite`. The blueprint verify line needs that flag. Location files do not enter the itinerary loader, because that loader rejects unknown assertion keys and the twelve Darjeeling cases must stay `itinerary_preference`.
- `PlaceSearchResult` has no coordinates. The area filter runs on loaded `Place` rows. `search_places()` in `places_index.py` is not given a geo argument.
- `Destination` has no bbox. A generate body with no anchor cannot build a `city_boundary`. It uses the disclosed 15 km city fallback. It does not geocode again and it does not use 30 km.
- `src/config.py`, `.env.example`, `src/main.py`, `src/core/middleware/rate_limit.py`, and `scripts/run_evals.py` sit outside the §9 path cells. The routes, the budget, and the suite flag cannot live anywhere else. This is the same wiring exception 3.1 used for settings.
- The trips spec currently says base coordinates add no columns. This change replaces that sentence. The columns are the ones §8.1 already names.
