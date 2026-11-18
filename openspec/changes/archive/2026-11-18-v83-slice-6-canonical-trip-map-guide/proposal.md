## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §6.6, §9 rows **6.1–6.5**, §10 exit line on one ID space) is the next product slice. This is not a new trip model. `Trip` / `TripPlace` already carry `place_id`, `order_in_day`, and `polyline`, and GeoJSON already copies `place_id` and `trip_place_id`. What is missing is a flag-gated status on that same row, an honest geometry label, edit validation that cannot publish a broken day, and a version so two edits cannot silently overwrite each other. `docs/context.md` records Slices 1–5 as implemented behind flags. `CANONICAL_TRIP_V2_ENABLED` is still absent from `Settings`.

## What Changes

- Row **6.1**: write `docs/v8.2/canonical_id_mapping.md` from the live symbols. Canonical place id is `places.id` / `TripPlace.place_id` / GeoJSON `properties.place_id`. Stop row id is `TripPlace.id` / GeoJSON `properties.trip_place_id`. `order_in_day` is the route order. Narrative prose in `write_narrative` is names, not an ID list; unknown UUIDs stay stripped. There is no separate guide-agent UI (`docs/v8.2/repository_audit.md` §4). Record that and continue. Do not add a guide LLM.
- Row **6.2**: additive `trip_places.stop_status` (`confirmed`, `suggested`, `removed`, `user_added`), server default `confirmed`. Behind `CANONICAL_TRIP_V2_ENABLED` (default false). Flag off omits the field and keeps today's routed rows, hard delete, and JSON shape. Flag on, suggestions are `dropped_stops` from the save that already ran, stored on the same table with the canonical `place_id`, and they never enter the route, the schedule, or GeoJSON. Promoting one uses the existing `POST /api/v1/trips/{id}/days/{day}/stops`. No new HTTP path.
- Row **6.3**: record `geometry_provenance` (`osrm`, `haversine_estimate`, `none`) when a polyline is written. Flag off, GeoJSON stays the frozen FeatureCollection. Flag on, a LineString is emitted only for real OSRM geometry and gains the additive property `geometry_provenance=osrm`. A haversine day stays Point-only and is never drawn as a road.
- Row **6.4**: the four existing day edits already recompute schedule, legs, and polylines, roll back on failure, and write `TripEditEvent`. Flag on, they also run validator V2 and roll back when a finding has `blocks_publish`. `VALIDATOR_V2_ENFORCE` stays false for generate. Current routing backends are fail-soft, so a null polyline does not fail the edit as `MISSING_ROUTE_GEOMETRY`. An OSRM miss stays HTTP 200 with provenance `none`.
- Row **6.5**: include optimistic concurrency. The audit shows last-write-wins: the four edit routes load, mutate, and commit a whole day with no version check. Additive `trips.version` (default 1). Flag on, `TripOut.version` plus `ETag`, and `If-Match` or `expected_version` mismatch returns 409 `trip_version_conflict`. A client that sends neither still succeeds. Flag off, the JSON key and the check are absent.
- No **BREAKING** change to paths, SSE event names, flag-off JSON, or flag-off GeoJSON.

## Capabilities

### New Capabilities

- `canonical-trip-identity`: flag, stop status, suggestion-versus-routed rule, geometry provenance values, trip version, and the ID mapping document (rows 6.1–6.5).

### Modified Capabilities

- `trips-http-crud-geojson`: flag-off body unchanged; flag-on fields, GeoJSON property, and 409 version conflict on the existing trip routes.
- `trips-repository-service`: same-transaction suggestion rows, status on `TripPlace`, version column, schema keys omitted when the flag is off.
- `p7-trip-edit-replan`: flag-on edits use routed rows only, promote a suggestion through the existing add route, soft-remove, and roll back on a blocking V2 finding.
- `route-geometry-polyline`: provenance stored at write time; flag-on GeoJSON withholds a line that is not OSRM.
- `database-migrations`: one additive revision for `stop_status`, `geometry_provenance`, and `trips.version`.

## Impact

- **Work surface:** `guideagent` only. Frontend selection, day highlight, and edit round-trip are the sibling change `v83-slice-6-6-trip-map-selection`. The parent vault change is `v83-slice-6-canonical-trip-boundary`. Apply backend first, then frontend. Two module PRs.
- **Code:** `src/trips/models.py`, `src/trips/schemas.py`, `src/trips/service.py`, `src/trips/repository.py`, `src/trips/router.py`, `src/trips/exceptions.py`, `src/config.py`, `.env.example`, `src/planner` save path only where `save_from_state` already persists a trip, Alembic revision, `docs/v8.2/canonical_id_mapping.md`, `docs/FE_guide.md`, `docs/context.md`.
- **Tests:** `pytest tests/trips -v`, `pytest tests/trips -k geojson`, `pytest tests/trips -k concurrency`, and the frozen snapshot tests with no `--update-baseline`.
- **Settings added:** `CANONICAL_TRIP_V2_ENABLED=false`. One cap for how many dropped stops become suggestions, default 3, in `Settings` (not a literal in the service).
- **No new package, no new route, no second trip table, no change to `uq_trip_place`.**

## Non-goals

- No Slice 7 reasoning agent, no Slice 9 lodging or media HTTP, and no stay-block copy change.
- No new guide LLM and no narrative that emits place ids. `write_narrative` stays a prose bookend.
- No flip of `CANONICAL_TRIP_V2_ENABLED`, `VALIDATOR_V2_ENFORCE`, `TRAVEL_ENGINE_V2_ENABLED`, or `READINESS_V2_ENABLED`.
- No new finding code. Edits call `collect_findings`.
- No crow-flies LineString, including under `haversine_estimate`.
- No SSE event rename and no change to the public GeoJSON geometry types.
- No enablement of the flag in a shared environment before the frontend sibling can filter `stop_status`.

## Constraints

From `AGENT.md` and the v8.3 invariants:

- Router calls `TripService` only. GeoJSON stays a raw FeatureCollection, not `ApiResponse` (existing envelope exception).
- `travel_engine/` stays pure. Provenance is chosen where the routing provider result is already known (`fallback_used` / `None` polyline), not inside the optimizer.
- LLM still must not invent place ids, coordinates, order, or times. Suggestions use `dropped_stops` place ids the engine already produced.
- Flag read only through `get_settings()`.
- Flag-off generate, trip JSON, and GeoJSON stay identical to the frozen snapshots (row 6.2 stop line is a payload break).
- Version check stays backward compatible for a client that omits `If-Match` and `expected_version` (row 6.5 stop line).
- Do not add a `RouteLeg` field. Slice 4.4 already locked that.

## Decisions recorded

- **6.5 is in scope.** Overlapping reorder, remove, add, and reoptimize are last-write-wins today. `updated_at` is not compared. The version column is the smallest additive fix that still lets an old client through.
- **Suggestions are dropped stops, not a new agent.** The audit found no guide-agent surface. A dropped stop already has a canonical `place_id` and was refused a place on the route. That is the suggestion list. Slice 9 may later attach lodging with the same `suggested` status. This slice does not ingest lodging.
- **Validator V2 on edits follows this flag, not `VALIDATOR_V2_ENFORCE`.** Generate stays in shadow. An edit that would publish a blocking finding rolls back. `MISSING_ROUTE_GEOMETRY` stays off the edit path: haversine, hybrid, and osrm are all fail-soft, and the existing reoptimize contract is HTTP 200 when the road line is missing.
