## Context

See `proposal.md` for why. Today `TripPlace` is one row per `(trip_id, place_id)`, every row is a routed stop, remove hard-deletes, and `build_geojson` is decode-only. `OsrmRoutingProvider.route_polyline` returns `None` when `fallback_used` is true, so a haversine day never has a polyline. Day edits already recompute schedule and legs inside one transaction and roll back on `TripEditValidationError`. `collect_findings` exists and generate still shadows it behind `VALIDATOR_V2_ENFORCE=false`. Frozen snapshot tests compare the full JSON body.

## Goals / Non-Goals

**Goals:**

- Add status, provenance, and version on the existing tables, gated so flag-off JSON and GeoJSON stay byte-identical to the snapshots.
- Keep suggestions, markers, and route stops on `place_id` / `trip_place_id`.
- Make a failed edit, including a blocking V2 finding, leave the trip unchanged.

**Non-Goals:**

- A guide LLM, a new route, a second place table, or a `RouteLeg` field.
- Promising road geometry. A missing polyline stays a successful Point-only day.

## Decisions

### 1. Flag-off JSON omits keys in the existing wrap serializer

`TripOut._serialize` already drops null `discovery_anchor` and `search_area`. The same serializer drops `version` when the flag is off, and `TripPlaceOut` drops `stop_status` and `geometry_provenance` when the flag is off. The database still stores the server defaults (`confirmed`, version `1`, provenance null).

Alternative: always emit the new keys. Rejected because `tests/snapshots` compares the whole body and row 6.2 stops if the payload shape breaks the frontend.

### 2. Status and provenance are Postgres enums, matching `trip_status` and `edit_type`

`stop_status` is a non-null enum defaulting to `confirmed`. `geometry_provenance` is a nullable enum. `trips.version` is a non-null integer defaulting to 1. The unique constraint stays, so a suggestion and a routed stop cannot both exist for one place. Non-routed rows use `order_in_day=0`. Routed rows stay 1-based.

Alternative: a side table of suggestions. Rejected because §6.6 requires one id space, and Slice 9 needs the same `suggested` value later.

### 3. Suggestions are capped dropped stops inside `save_from_state`

After the routed inserts, and only when the flag is on, read `dropped_stops` already on the route state. Skip ids that are routed. Take at most `CANONICAL_TRIP_MAX_SUGGESTIONS_PER_DAY` (default 3) per day. Insert `suggested`, `order_in_day=0`, polyline null, provenance `none`, in the same transaction. No new tool and no LLM.

Alternative: a post-generate HTTP call. Rejected because the blueprint forbids a path that would let suggestions auto-enter the route, and the dropped ids are already in memory at save.

### 4. Provenance is chosen in `TripService`, not in `travel_engine`

At each polyline write (save and day edit): non-null polyline means `osrm`, because `route_polyline` already returned `None` on fallback. Null polyline with `ROUTING_BACKEND=haversine` means `haversine_estimate`. Null polyline with `osrm` or `hybrid` means `none`. `build_geojson` only reads the stored value. Flag on, a day LineString is emitted only when every routed leg is `osrm` and decodes. Flag off, today's concatenation stays, with no provenance property.

Alternative: store a straight haversine polyline and label it. Rejected because the map contract forbids crow-flies.

### 5. Version is checked in the service; the router only parses the header

Edit methods gain an optional expected version. The router reads `If-Match`, strips optional quotes, and passes one integer. `ReorderStopsIn` and `AddStopIn` gain optional `expected_version`. If the header and the body are both set and differ, the router raises 422 before the service runs. The service compares against `trips.version` before mutation. Mismatch raises `TripVersionConflictError` (409, `trip_version_conflict`). Success increments version in `_persist_day_and_audit` only when the flag is on. GET and successful edits set `ETag` to the quoted integer only when the flag is on.

A missing header and a missing body field is the legacy client: the write proceeds and, when the flag is on, the version still increments so the next versioned client sees the change.

Alternative: require `If-Match` on every edit. Rejected by row 6.5. Alternative: compare `updated_at`. Rejected because the body does not carry it today and clock ties are a worse token than an integer.

### 6. Flag-on edits use routed rows and reuse the unique row

Reorder and remove look only at `confirmed` and `user_added`. Remove sets `removed`, clears the polyline, sets `order_in_day=0`, and reoptimizes the rest. It does not hard-delete. Add of `suggested` or `removed` updates that row to `user_added` and optimizes. Add of an already routed place stays 409 `stop_already_on_trip`. Flag off keeps hard-delete and the current conflict rule. The hard-delete repository helper stays for the flag-off path.

### 7. Validator V2 on edits does not treat a missing line as fatal

When the flag is on, `_validate_full_trip` still calls `validate_trip`, then `collect_findings` with `geometry_promised` all false. Any other `blocks_publish` finding raises `TripEditValidationError` and the existing rollback runs. `VALIDATOR_V2_ENFORCE` is not read on this path. Search-area arguments are passed only when `trip.search_area` already has a center and a radius. No radius is invented.

Alternative: promise geometry for `hybrid` and `osrm`. Rejected because an OSRM outage would turn today's HTTP 200 fail-soft edit into a 422, which fights the named fallback in `geo/osrm.py`.

### 8. No new I/O

This slice adds no httpx call. Polyline timeouts and the haversine fallback stay inside `src/geo/osrm.py`. `build_geojson` stays free of network I/O. `travel_engine` stays pure.

## Risks / Trade-offs

- [Flag turned on before the frontend sibling filters `stop_status`] → Suggestions appear inside `places` and an old client may render them as stops. Mitigation: default false, and do not enable the flag in a shared environment until `v83-slice-6-6-trip-map-selection` is deployed. The frontend treats a missing `stop_status` as routed.
- [Flag-on GeoJSON drops a partial line that flag-off would concatenate] → A day with one `osrm` leg and one `none` leg has points only. Mitigation: flag default false; the label would have been a lie.
- [Legacy client while the flag is on can still overwrite] → That is the row 6.5 compatibility rule. Mitigation: the version still increments, so a client that does send `If-Match` conflicts on the next try.
- [Enum growth] → A new status needs a migration. Slice 9 reuses `suggested` and does not need a new value for lodging.

## Migration Plan

1. Alembic upgrade adds the three columns and backfills `confirmed` and version `1`. Downgrade drops only those columns.
2. Deploy with `CANONICAL_TRIP_V2_ENABLED=false`. Rollback of behavior is the flag. Rollback of schema is `alembic downgrade -1` only before code that reads the columns is the sole writer. After that, leave the columns and turn the flag off.
3. Frontend ships second, still correct while the keys are absent.
4. Update `docs/FE_guide.md` trip and GeoJSON sections and `docs/context.md` next-step line in the same backend change.

## Open Questions

None. The suggestion source, the version compatibility rule, and the fail-soft geometry rule are fixed above.
