## Context

See proposal.md — Why. `LocationIntelligenceService.search` and `search_area_for` already return `LocationResolution` and `SearchArea`. `POST /api/v1/planner/generate` still defaults `base_lat`/`base_lng` from the destination center, and `search_places` falls back through `PlaceRepository.find_within_radius` at `SEARCH_DEFAULT_RADIUS_KM` (30) around that base. `PlaceSearchResult` has no coordinates. `Destination` has name, country, lat, lng, and `osm_place_id`, and no bbox. `request_material` hashes destination, normalized text, days, and the rounded base. Accommodation is already excluded. Trip JSON is built in `TripOut.from_trip`.

## Goals / Non-Goals

**Goals:**

- One flag branch in the planner router: off leaves the current strings, the current retrieval radius, and the current trip JSON; on builds one server-owned `SearchArea` and stores it beside the trip base.
- Three routes that are a thin `ApiResponse` over the existing service, 404 when the flag is off.
- A location suite the Darjeeling itinerary run does not load.
- A compose-page contract the frontend can implement without replacing destination resolve.

**Non-Goals:**

- See proposal.md — Non-goals. In particular, no geo index in Qdrant and no shapely.

## Decisions

### 1. The router owns the flag branch

`src/planner/router.py` reads `LOCATION_V2_ENABLED` once, before the graph. Off: call `PlannerService.generate` exactly as today and pass an empty location suffix into the idempotency and cache helpers. On: build the area, put plain dicts on the initial travel state (`discovery_anchor`, `search_area`), and pass a non-empty suffix only when the body sent an anchor or a radius. `request_material` keeps its current signature and gains an optional suffix that defaults to empty, so every existing caller stays byte-identical.

`DestinationService` gains a read-only mapper from a destination row to a city `ResolvedLocation` (provider `catalog`, no bbox, no commit). The router uses it for a body with no anchor. It does not call `search` or `resolve` on that service, and it does not geocode.

Alternative: geocode the destination name on every flag-on generate so a city can get a real bbox. Rejected. That adds a Nominatim call to the hot path and can change the anchor under a client that already picked a destination id.

Alternative: treat `base_lat`/`base_lng` as the anchor when the flag is on. Rejected. That is the stop condition in row 3.4. The base stays the route start. `_resolve_base` does not read the new columns.

### 2. Confirmation is a fresh search, not a stored handle

There is no location id to round-trip. For provider `nominatim` or `catalog`, the router calls `LocationIntelligenceService.search` with `query` or else `canonical_name`, then keeps the candidate whose provider and provider id match. Anything else is HTTP 422 `anchor_not_confirmed` before `destination_not_ready`'s sibling checks would start the graph. This check runs after the destination floor only so a missing destination stays 404 and an unready destination stays 409. A country or region raises the existing `OversizedAdminError` and the router maps it to HTTP 422 `oversized_admin`. `ExternalServiceError` from Nominatim 403/429 still propagates. A library timeout (`not_found` / `geocoder_timeout`) is `anchor_not_confirmed`, not a substituted city.

Provider `user` with type `map_pin` skips the geocoder. Latitude and longitude are range-checked (`invalid_coordinates`). Radius follows `build_search_area`, which already clamps to `LOCATION_MAX_RADIUS_KM`.

A posted radius replaces the policy radius only when the built strategy is `radius`. A city or neighborhood boundary is kept. Generate does not accept a client polygon. The preview route does, and it uses the existing polygon checks.

Alternative: persist the preview payload as the trip area. Rejected. The preview can be stale or widened. The stored area is always the one generate built.

### 3. Filter loaded places, do not change the Qdrant query

`search_places()` in `places_index.py` stays destination-scoped and keeps its signature. A new helper there takes already loaded places and a containment predicate and returns the subset. The DISCOVER tool calls it only when state has a search area. Containment lives in `location_intelligence` as a pure function: haversine against `radius_km`, or a ray cast on the stored rings. No new package.

PostGIS fallback when an area is present calls the existing `find_within_radius`. Radius strategy: anchor point and `area.radius_km`. Boundary or polygon: covering radius is half the diagonal of the ring's bounding box, in kilometers, then the same predicate drops points outside the ring. The tool must not pass `30` or the trip base on that branch. When state has no area, the tool keeps today's base and `SEARCH_DEFAULT_RADIUS_KM`.

`travel_engine` is not given the area. Candidates that reach it are already inside. `tests/travel_engine/test_properties.py::test_area_respect` stops skipping and asserts the pure predicate. The engine package still does not import `location_intelligence`. The isolation test that required the skip is updated to require that import ban instead.

Alternative: a new `ST_Contains` repository method. Rejected for this slice. The allowed repository call already exists, and the precise test is in Python on the rows it returns.

### 4. Columns are nullable and absent from JSON until set

One Alembic revision adds `trips.discovery_anchor` and `trips.search_area` as nullable JSONB. No server default and no backfill. `save_from_state` writes them only from state dicts the flag-on path put there. Preferences keep `base_lat`/`base_lng` and do not gain the area.

`TripOut.from_trip` omits those two keys when the values are null and leaves every other null field as it is serialized today. Flag-off snapshot bodies therefore do not grow. GeoJSON is unchanged.

### 5. Routes match destinations search, and they are dark when the flag is off

`src/location_intelligence/router.py` is included from `src/main.py`. The handler checks the flag first and returns 404 before constructing the service, so Nominatim is not called. Success uses `ApiResponse`. 422 uses the existing error envelope and the codes in the spec (`oversized_admin`, `invalid_polygon`, `invalid_coordinates`, `anchor_not_confirmed`).

The rate-limit table gains three exact paths. The numbers are the existing destinations-search settings (20 / 60). Only the three path strings are new settings, documented in `.env.example`. Auth is the same as `GET /api/v1/destinations/search`: no login.

Resolve with `provider` and `provider_id` is the confirmation call. Resolve without them is the library's auto-resolve, including `ambiguous` and `requires_confirmation`.

Resilience is the service that already exists: `asyncio.wait_for` around `geocode_search` at `SEARCH_GEOCODE_TIMEOUT_SECONDS`, tenacity and the empty-list fallback inside the geocoder, timeout becomes `not_found` / `geocoder_timeout`, 403/429 stay `ExternalServiceError`. These routes add no retry of their own. Search-area for a map pin or a posted polygon does not call the network.

### 6. The location suite is a second folder

`--suite location` on `scripts/run_evals.py` reads `evals/golden/location/*.json` with a small loader that is not `load_golden_cases`. It runs the pure resolver, the search-area builder, and the containment predicate on fixtures checked into that folder. It does not import `PlannerService`. `--replay` is accepted so the blueprint command works, and it does not open `evals/replay`. The default destination run is unchanged when `--suite` is omitted.

`test_area_respect` and this suite are both in scope. The suite is what `run_evals.py --replay --suite location` gates. The property test is the engine-file proof that the skip is gone.

### 7. The picker sits on compose, and destination resolve stays

Home and explore keep `GET /api/v1/destinations/resolve` as the way to choose `destination_id`. The new panel is on the compose page, after that id exists. If `POST /api/v1/locations/search` returns 404, the panel is not shown and generate sends the body it sends today. If it returns a resolution, the panel lists candidates with the location type as a visible label. Choosing one calls resolve with that provider and provider id. The radius control is editable for a radius strategy and for a map pin, and it is not editable when the preview strategy is `city_boundary` or `admin_boundary`. Preview calls search-area and shows strategy, radius, `fallback_used`, and description in text. It does not add a map SDK. The copy states that the anchor is where search runs and the route starts at the trip base, which is the destination center when the user left base empty. The panel must not write the anchor into `base_lat` or `base_lng`.

The frontend regenerates `types/generated/api.d.ts` from the backend OpenAPI. Contract tests parse checked-in envelopes for the three routes and the trip payload with and without the new keys. That work is the second pull request, under the frontend OpenSpec change `v83-slice-3-6-location-picker`. This backend change writes `docs/FE_guide.md` and `docs/blueprint_frontend.md` so the contract exists before that PR.

### 8. Completion sync is the status rows, after the proofs

After the verify commands pass, update `docs/context.md` (next blueprint row is Slice 4; flag default still false) and the `trips.search_area`, `trips.discovery_anchor`, and location-route rows in `docs/v8.2/repository_audit.md`. Do not mark rows 4.x done. Do not edit the blueprint table.

## Risks / Trade-offs

- [A destination-only flag-on trip searches 15 km, not the old 30 km] → That is the exit gate. The description says the fallback was used. Flag off keeps 30 km. Operators who need the old radius leave the flag off.
- [A city bbox is unavailable, so flag-on legacy generate never uses `city_boundary`] → Recorded in the proposal. A later provider field can fill a bbox. This slice does not geocode to invent one.
- [Ray-cast on a bbox rectangle is not a municipal polygon] → The builder already stores that rectangle and says so. Containment matches the geometry we store.
- [Covering-radius PostGIS can read extra rows] → The predicate drops them before `candidate_pois`. A test includes a point inside the covering circle and outside the ring.
- [Confirming a candidate calls Nominatim again] → Same timeout and 403/429 behavior as the library. The destination-only path does not pay that call. The preview and the generate confirmation are the calls the user asked for by selecting a hit.
- [Optional PlanRequest fields change the OpenAPI schema] → They are optional. Flag-off snapshots compare responses, not a frozen schema file. The frontend regenerates types in its own PR.
- [Null-omission on `TripOut` drops a key a client expected to see as `null`] → Flag-off clients never saw the key. Flag-on clients read it only when it is an object.
- [Someone sets the flag on before the frontend PR] → Routes work. Generate accepts the new fields and still accepts the old body. The compose page simply does not send them until the second PR. Retrieval for old bodies uses the disclosed 15 km fallback.

## Migration Plan

Deploy order: run the Alembic upgrade, then deploy the API. Existing trips keep nulls. The previous API process does not select the new columns by name, so extra columns on `trips` are compatible. Rollback of behavior is `LOCATION_V2_ENABLED=false` (routes 404, generate ignores anchors, new saves write nulls). Drop the columns only after the process that reads them is gone: deploy the old build, then `alembic downgrade -1`.

Frontend rollback is reverting that PR. The API flag can stay off either way.

## Open Questions

None. The frontend owner and the contract are this change. A question that would move the picker back onto home resolve, or that would store the client polygon, would change the specs and is already decided above.
