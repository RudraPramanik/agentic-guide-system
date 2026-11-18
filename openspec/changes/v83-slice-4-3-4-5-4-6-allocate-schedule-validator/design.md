## Context

See `proposal.md` for why. Checkout facts that shape the approach:

- `allocate_days` already pre-clusters at `CLUSTER_RADIUS_KM` (10), caps places at 6, caps visit time at `ACTIVE_DAY_VISIT_BUDGET_MIN` (450 = 8 h minus `MIN_TRAVEL_BUFFER_MIN`), caps morning-only at 2, and omits a cluster farther than 10 km from an occupied day.
- `build_day_schedule` already consumes `RouteLeg.duration_min` (not a fixed gap), inserts one lunch, and extracts at most two morning-only stops. It has no day-end omit and no hours fields.
- `validate_trip` returns string `errors` / `warnings` / `passed`. `validate_itinerary` sets `ToolResult.ok` from `passed`. Orchestration merges only `_MERGE_KEYS`; `validation_result` is one of them. `tool_trace` stores `ToolTraceEntry`, not the full data dict.
- `TRAVEL_ENGINE_V2_ENABLED` already exists and defaults false. `VALIDATOR_V2_ENFORCE` does not. `TravelState.search_area` is an optional dict from Slice 3. Trip edits call the schedule and validator with today's signatures.
- Specs for this change live under `specs/`. This design only records decisions those specs do not pin down.

## Goals / Non-Goals

**Goals:**

- One injected `v2_enabled: bool = False` on allocate and schedule, and a pure findings collector the tool calls.
- Shadow publish bit stays the v6.1 result. Enforce is a second, tested branch.
- Prove every §6.5 code with a valid fixture and an invalid fixture.

**Non-Goals:**

- A second allocator algorithm when the comparison report names no miss.
- Parsing OSM hours, polygons inside `travel_engine`, or optimizer return-to-base legs.
- Putting findings inside `validation_result`.

## Decisions

### 1. Compare first, then delegate

**Choice:** First implementation task writes `docs/v8.2/allocator_v2_comparison.md` from the current function and the constants above. If it records no cap miss and no far-cluster miss, `allocate_days(..., *, v2_enabled=False)` stays the body, and `v2_enabled=True` calls that same body. Do not change `CLUSTER_RADIUS_KM`, `MAX_PLACES_PER_DAY`, or the 450-minute budget.

**Why:** Row 4.3 says compare before tuning, and the tree already matches the locked caps. Alternatives rejected: (a) a new clustering package — row stop; (b) raising the budget to 480 so the label says "8 h" — loosens a shipped cap; (c) a divergent V2 pack with no named miss — would break flag-on coherence equality for no acceptance gain.

### 2. Schedule V2 is a second pure function; preserve-order stays legacy

**Choice:** Keep today's clock in `_schedule_legacy`. `v2_enabled=True` and `preserve_order=False` use a V2 clock: each hop adds `duration_min + MIN_TRAVEL_BUFFER_MIN`, one lunch, morning extract unchanged, drop a stop whose visit would end after `DAY_END_TIME` (`16:00`). `preserve_order=True` always uses the legacy clock, even if a caller also passes `v2_enabled=True`.

**Why:** Edit reorder must keep the client sequence. Alternatives rejected: applying day-end omission on preserve-order — drops a stop the client asked to keep; adding the buffer inside the legacy clock — changes flag-off times.

### 3. Hours are optional fields, not a parser

**Choice:** Add `opening_hours_status: Literal["verified","unknown","malformed"] = "unknown"`, `opening_open: str | None = None`, `opening_close: str | None = None` on `PlaceCandidate`. V2 waits until `opening_open` only when status is `verified`, both strings are present, and the visit still ends by close and by `DAY_END_TIME`. Otherwise omit that stop. Any other status times at the arrival clock and must not set an arrival note that says the place is open. No OSM parse, no new package.

**Why:** §8.3 and row 5.3 own parsing. Row 4.5 still needs a verified-hours proof. Alternatives rejected: treating unknown as 00:00–23:59 — that claims "open"; importing a parser — row stop if it is a heavy dependency.

### 4. Findings module plus an unchanged `validate_trip`

**Choice:** New `src/travel_engine/findings.py` holds `Severity`, `ValidationFinding`, the code registry, and `collect_findings(...)`. `validate_trip` stays the string chain. `collect_findings` may call the existing check predicates for the five overlapping codes and adds the rest itself. It takes optional plain arguments: `search_center: tuple[float, float] | None`, `search_radius_km: float | None`, `geometry_promised: bool`, and `leg_durations_min: list[int] | None` per day (aligned to consecutive hops). Missing option ⇒ that code is not emitted.

Predicates the specs name only by code:

- `ROUTE_SCHEDULE_MISMATCH`: emit only when leg durations were supplied and a scheduled gap from previous visit end to the next start is shorter than that leg's `duration_min`. A longer gap (lunch or buffer) is not a mismatch.
- `UNREALISTIC_VISIT_SEQUENCE`: starts are strictly increasing and a stop still starts before the previous stop's start plus `visit_duration_min`.
- `INSUFFICIENT_EVIDENCE`: `evidence_count == 0`, severity `info`, `suggested_action` null.
- `OVERLOADED_DAY`: stop count above `MAX_PLACES_PER_DAY` or visit sum above `ACTIVE_DAY_VISIT_BUDGET_MIN`.
- `MISSING_PLACE_ID`: stop place id is `BASE_SENTINEL_ID`.
- `MISSING_ROUTE_GEOMETRY`: `geometry_promised` is true and the caller flags the day geometry missing.

`suggested_action` map: `drop_weakest_stop` for duplicate, invalid coordinates, missing id, out of area, excessive travel, overloaded day, geo-incoherent day; `reoptimize_routes` for hours conflict, missing geometry, route/schedule mismatch, non-chronological, unrealistic sequence, morning-only; `expand_poi_search` for no anchor; null for unknown hours and insufficient evidence.

**Why:** G14 needs one registry. Reusing the v6.1 predicates keeps the string errors and the findings from drifting. Alternatives rejected: replacing `ValidationResult.errors` with findings — breaks flag-off `ok`; importing `SearchArea` — purity break.

### 5. Tool boundary owns both flags

**Choice:** `build_route` and `build_schedule` read `TRAVEL_ENGINE_V2_ENABLED` via `get_settings()` and pass `v2_enabled=` into allocate and schedule. They do not pass it into `optimize_route`. `validate_itinerary` always calls `collect_findings` after `validate_trip`. It reads `VALIDATOR_V2_ENFORCE` (default false) via `get_settings()`.

While enforce is false, `ok`, `errors`, `warnings`, and `validation_result` are the v6.1 objects only. Findings are logged with the existing structlog logger and returned as `data["v2_findings"]`. That key is not added to `_MERGE_KEYS`. While enforce is true, `ok` is false when `passed` is false or any finding has `blocks_publish` true. `validation_result` stays the v6.1 object in both modes so `finish_plan` and the agent prompt do not gain a new shape.

Search area: if `state["search_area"]` has numeric anchor lat/lng and `radius_km`, pass those floats. If the area is polygon-only (`radius_km` absent), pass `None`. Geometry promised: true only when the route day has a non-empty polyline and `used_fallback` is false.

**Why:** Same injection pattern as rows 4.1–4.2. Merging findings into `validation_result` would change replayed agent context with the default flag. Alternatives rejected: computing findings only when enforce is true — the flag's off state is defined as shadow, not as "do nothing"; calling `point_in_search_area` inside `travel_engine` — imports location intelligence into the pure package.

### 6. No new I/O

**Choice:** No HTTP client, no timeout, no tenacity retry. Routing durations stay on the `RouteLeg` values the optimizer already returned. Rollback is both flags false, which is the default.

**Why:** Rows 4.5 and 4.6 stop if timezone support or validator I/O shows up. There is no new upstream to fail.

## Risks / Trade-offs

- [Comparison finds a real cap miss after all] → Tune only that miss behind `v2_enabled=True`, keep mode-off identical, and record the miss in the comparison note. Do not retune in silence.
- [Per-hop buffer makes V2 days shorter than flag-off] → Accepted. Day-end omission is the "fits day" proof. Flag-off bytes stay on the legacy clock.
- [Polygon search areas emit no `OUT_OF_SEARCH_AREA`] → Accepted for this slice. Do not invent a covering radius. A later change can pass precomputed outside ids without putting `SearchArea` in the engine.
- [Shadow log volume on `evidence_count == 0`] → Info finding, not a publish change. Do not start suggesting `expand_poi_search` for every stop.
- [`--replay` drops because a merged key changed] → Stop. Remove the merge. Do not update the baseline to hide it.
- [Enforce-on tests mutate process settings] → Patch `get_settings` in the tool test. Do not change the default in `config.py`.

## Migration Plan

1. Land with `VALIDATOR_V2_ENFORCE=false` and the existing engine flag false.
2. Replay gate must exit 0 before any doc stamp that says the rows are done.
3. Rollback: set both flags false. No migration to reverse. Do not flip enforce on in this change.

## Open Questions

None that change the specs or the task order. Polygon containment and the enforce-on soak are later slices (4.7 / operator soak), not this design.
