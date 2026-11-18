## 1. Identity map and flag

- [x] 1.1 Write `docs/v8.2/canonical_id_mapping.md` from live `Trip`, `TripPlace`, GeoJSON properties, and `write_narrative` (names, not ids). Name the frontend change `v83-slice-6-6-trip-map-selection` and the parent change `v83-slice-6-canonical-trip-boundary`.
- [x] 1.2 Add `CANONICAL_TRIP_V2_ENABLED=false` and `CANONICAL_TRIP_MAX_SUGGESTIONS_PER_DAY=3` on `Settings` and in `.env.example`. Read them only through `get_settings()`.

## 2. Schema

- [x] 2.1 Add `Trip.version` (integer, not null, default 1), `TripPlace.stop_status` (enum `confirmed|suggested|removed|user_added`, default `confirmed`), and nullable `TripPlace.geometry_provenance` (`osrm|haversine_estimate|none`). Keep `uq_trip_place`.
- [x] 2.2 Add one Alembic revision that backfills existing trips to version 1 and existing stops to `confirmed`, and whose downgrade drops only those three columns.
- [x] 2.3 Extend `TripOut` / `TripPlaceOut` and the wrap serializer so the flag-off JSON omits `version`, `stop_status`, and `geometry_provenance`. Add optional `expected_version` on `ReorderStopsIn` and `AddStopIn`.
- [x] 2.4 Add `TripVersionConflictError` (409, `trip_version_conflict`).

## 3. Save, geometry, and reads

- [x] 3.1 In `TripService`, set provenance at polyline write time: non-null polyline → `osrm`; null and haversine backend → `haversine_estimate`; null and `osrm` or `hybrid` → `none`. Do not write a straight-line polyline.
- [x] 3.2 When the flag is on, `save_from_state` writes routed stops as `confirmed` and, in the same transaction, up to the cap of dropped stops per day as `suggested` (`order_in_day=0`, no polyline, provenance `none`), skipping ids already routed. Flag off writes no suggestion rows.
- [x] 3.3 `build_geojson` stays decode-only. Flag off matches today's points and concatenated lines with no provenance property. Flag on emits points only for `confirmed` and `user_added`, and a LineString only when every routed leg on that day is `osrm`, with property `geometry_provenance=osrm`.

## 4. Edits and version

- [x] 4.1 Flag on, reorder and remove consider only routed rows. Remove sets `removed` and recomputes; it does not hard-delete. Add of `suggested` or `removed` reuses the row as `user_added`. Add of an already routed place stays 409 `stop_already_on_trip`. Flag off keeps hard-delete and today's conflict check.
- [x] 4.2 Parse `If-Match` in the trips router and pass one expected version into the service. Header and body both set and unequal → 422 before mutation. Flag on, mismatch → 409 and no `TripEditEvent`. Missing version still applies and increments `trips.version`. Flag off ignores the header and does not increment.
- [x] 4.3 Flag on, after `validate_trip`, call `collect_findings` with geometry not promised. Any other `blocks_publish` finding rolls back with 422. Do not read `VALIDATOR_V2_ENFORCE` on this path. A null polyline on `haversine`, `hybrid`, or `osrm` still returns 200.
- [x] 4.4 Set `ETag` to the quoted version on GET and on successful edits only when the flag is on.

## 5. Proof

- [x] 5.1 Add tests for suggested versus routed, add-stop promotion, flag-on soft remove, flag-off hard delete, GeoJSON validity, haversine never labeled `osrm`, partial `osrm`/`none` day with no LineString, failed edit unchanged, matching `If-Match` increments, mismatch 409, and legacy edit without a version.
- [x] 5.2 Run `pytest tests/trips -v`, `pytest tests/trips -k geojson`, and `pytest tests/trips -k concurrency`. Run the frozen snapshot tests with no `--update-baseline`.
- [x] 5.3 Update `docs/FE_guide.md` trip and GeoJSON sections for the flag-gated keys, `ETag` / `If-Match`, and 409 `trip_version_conflict`. Update `docs/context.md` so the next-step line records Slice 6 behind the flag, default false, and does not claim the flag is on.
