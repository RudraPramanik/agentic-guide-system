## Context

P5 is complete (`docs/context.md`). Planner tools call `optimize_route` via `RoutingProvider.travel_matrix`, but nothing requests road geometry. Blueprint v6.1 and `TripPlace.polyline` / GeoJSON assume encoded polylines exist. Step **6.0** in `docs/steps/step6.md` is the locked cross-phase patch before 6.1 persistence.

Today's gap is larger than “add two fields”:

- `OptimizeResult` has no polyline fields.
- `OsrmRoutingProvider` / `FakeRoutingProvider` lack `route_polyline`.
- `build_schedule` emits `list[list[ScheduledStop.dump]]`, while step 6.0 and `write_narrative._place_ids_in_schedule` already expect **day dicts** with flat `place_id` / `stops`.

So 6.0 must both add geometry **and** normalize the schedule contract consumers will need in 6.1+.

Constraints (AGENT.md / blueprint):

- `travel_engine` pure — Protocol DI only; no `src.geo` imports.
- Geo only via `src/geo/` inside the planner adapter.
- No new packages; do not change `get_route` signature.
- Fail soft: missing geometry → `None`, never block itinerary generation.

## Goals / Non-Goals

**Goals:**

- Close the polyline gap for the final ordered day (leg + day polylines).
- Thread geometry into `TravelState.schedule` day-dict shape.
- Keep Fake/OSRM providers Protocol-complete so tests stay green.
- Leave a clean handoff for 6.1 `save_from_state` (`stop["leg_polyline"]` → `TripPlace.polyline`).

**Non-Goals:**

- Trips repository/service/router, claim, GeoJSON HTTP (6.1/6.3).
- Planner SSE / cache / Redis (6.2/6.4).
- New OSRM table/service API or geometry during permutation search.
- P7 edit/reoptimize HTTP.
- Preference-semantic cache keys or other post-MVP work.

## Decisions

### D1 — Geometry after order only (N+1 calls/day)

**Choice:** After the winning `ordered` list is final, call `route_polyline` once per consecutive pair (base→stop / stop→stop) plus once for the full path.

**Why:** Matches step 6.0; avoids O(n²) geometry during permutation scoring; reuses existing `get_route`.

**Alternatives considered:** Geometry inside every permutation (rejected — cost); single day polyline only (rejected — per-stop `TripPlace.polyline` needs leg geometry).

### D2 — `route_polyline` is fail-soft including exceptions

**Choice:** Adapter returns `None` when `fallback_used`, when `encoded_polyline` is missing, **or** when `get_route` raises. Optimizer never sees exceptions from geometry.

**Why:** Step 6.0 says never raise; `get_route` raises `ValueError` for &lt;2 waypoints — empty/edge days must not 500 the agent loop. Blueprint fallback posture: haversine / no-line degrade.

**Alternatives considered:** Let `ValueError` propagate (rejected — breaks fail-soft); return empty string instead of `None` (rejected — `None` is the locked “no geometry” signal).

### D3 — Schedule shape migration is in-scope for 6.0 (hardening)

**Choice:** Change `build_schedule` output to locked day dicts now; update `validate_itinerary` (and narrative helpers if needed) in the same change. Carry `leg_polylines`/`day_polyline` on route days from `build_route` so schedule can copy them.

**Why:** Without this, 6.1 would invent adapters or silently fail `save_from_state`. `write_narrative` already looks for day dicts + `place_id` — current list-of-lists is already inconsistent.

**Alternatives considered:** Defer reshape to 6.1 (rejected — leaves geometry stranded on `OptimizeResult` / route only); dual-write both shapes (rejected — complexity for one release).

### D4 — Flat stop dicts for persistence-ready schedule

**Choice:** Stops in schedule day dicts are flat (`place_id`, `name`, `lat`, `lng`, `category`, `order`, `travel_time_min`, …, `leg_polyline`), not nested `ScheduledStop` dumps. `validate_itinerary` reconstructs `ScheduledStop`/`PlaceCandidate` as needed for the pure validator.

**Why:** Matches step 6.0 + `save_from_state` field map exactly.

**Alternatives considered:** Keep nested `place` objects and teach 6.1 to dig (rejected — fights the locked mapping).

### D5 — No geometry on intermediate drop-retry attempts

**Choice:** Only the returned/final ordered list gets polyline calls.

**Why:** Drop-retry can call `travel_matrix` multiple times; geometry is display/persist only and must not multiply OSRM load.

### D6 — Fake default polyline

**Choice:** Shared `FakeRoutingProvider.route_polyline` returns a deterministic placeholder (e.g. `"fake_polyline"` or `f"poly_{len(waypoints)}pts"`) so existing tests need minimal churn; tests that assert None can override.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Schedule reshape breaks `validate_itinerary` / tool_loop tests | Update validator adapter + fixtures in same PR; run full `pytest` |
| Extra OSRM latency (N+1 calls/day) | Acceptable vs matrix cost; still ≪ permutation×geometry; fail-soft on timeout via existing `get_route` fallback → None |
| `total_distance_km` not on OptimizeResult today | Derive from consecutive winning legs when available; default `0.0` if unclear — do not invent geo |
| Narrative `_place_ids_in_schedule` previously missed nested `place.id` | Flat `place_id` fixes this; verify after reshape |
| Over-scoping into 6.1 persist | Hard stop: no trips service/router in this change |

## Migration Plan

1. Protocol + Fake + OsrmRoutingProvider.
2. Optimizer polyline population + unit tests + step 6.0 validation snippet / failure path.
3. `build_route` carry polyline fields on route days.
4. `build_schedule` emit day-dict schedule + polyline copy; fix `validate_itinerary`.
5. Adjust planner tests / smoke fakes; full pytest.
6. Stamp `docs/context.md`: 6.0 done, next **6.1** (do not mark all of P6 complete).

Rollback: revert the change branch; no DB migration in 6.0.

## Open Questions

- None blocking apply. Optional later: should `day_polyline` also be copied onto narrative `itinerary.days[]` under key `day_polyline` (write_narrative already preserves unknown structural keys like `polyline`)? **Recommendation during apply:** also preserve `day_polyline` when copying structural fields (one-line hardening; not a new API).

## Hardening suggestions (captured for apply / later)

Already folded into this design:

1. Schedule day-dict migration in 6.0 (not deferred).
2. Exception swallowing in `OsrmRoutingProvider.route_polyline`.
3. No geometry on discarded drop-retry attempts.
4. Empty ordered → zero geometry calls.

Suggested but **out of 6.0 code** (document only / later steps):

5. Blueprint `RoutingProvider` snippet still shows only `travel_matrix` — consider a small blueprint note when syncing docs (optional; step6 is build SoT for this patch).
6. 6.1 MUST use `stop["leg_polyline"]` only — never re-hit OSRM on save.
7. Developer manual refresh can wait until P6 ends (cadence), but context.md updates after 6.0 validate.
