## Context

Implement P4 steps **4.7–4.8** from the locked build contract `docs/steps/step4.md`. Planner SoT remains `docs/blueprint_final.md` v6.1 (Chain of Responsibility for validator; Adapter for OSRM outside `travel_engine`). Do **not** revise step4, step4-fix, or the blueprint in this change.

**Already shipped:** `protocols`, `travel_rules` (incl. `GEO_COHERENCE_MAX_STDDEV_KM`, `ANCHOR_MIN_SCORE`, morning/travel caps), `place_selector`, `day_allocator`, `route_optimizer` (`DroppedStop`, `OptimizeResult`), `schedule_builder` (`ScheduledStop`), CORS. P2 `geo/osrm.get_route` is real (tenacity → haversine × 1.4 with `fallback_used`).

**Still stubs (~1-line):** `src/travel_engine/trip_validator.py`, `src/planner/routing_provider.py`, `src/planner/tools/schemas.py`, `src/planner/tools/registry.py`.

**Doc guidance:** Use `step4.md` 4.7–4.8 as the only implementation contract. Where blueprint §4.8 mentions `state.used_osrm_fallback`, P4 follows step4: map onto `RouteLeg.used_fallback` only; TravelState flag is P5.

## Goals / Non-Goals

**Goals:**
- Ship `trip_validator` (4.7) and `OsrmRoutingProvider` + `ToolResult`/`execute_tool` skeleton (4.8) exactly per step4.
- Keep `travel_engine` pure after 4.8 (zero `src.geo` / httpx imports under that package).
- Land focused pytest for validator + provider + execute_tool stub covering ★ cases previewed in 4.9.
- Bump `docs/context.md` for 4.7–4.8 only; Next step = 4.9.

**Non-Goals:**
- Steps 4.9–4.10 (full P4 pytest plan, purity AST suite as a dedicated module if deferred, smoke, P4-complete context).
- Full PHASE_TOOLS / 12-tool registry, LangGraph, SSE, real tool bodies.
- Setting `TravelState.used_osrm_fallback` (no TravelState wiring in P4).
- HTTP routers; SQLAlchemy Place models inside the engine.

## Decisions

### D1 — Build contract is step4.md only
Copy types/APIs from steps 4.7–4.8. Reuse `ScheduledStop` from `schedule_builder`, `DroppedStop` from `route_optimizer`, constants from `travel_rules`, `RouteLeg`/`RoutingProvider` from `protocols`. No SQLAlchemy models in the validator.

### D2 — Chain of Responsibility (validator)
Each named rule is a separate pure function returning `list[str]` error messages. `validate_trip` runs the fixed chain, aggregates errors, then adds the dropped_stops **warning** (not error) when any day has non-empty `dropped_stops`.

Locked chain order (step4):
1. `check_daily_travel_cap`
2. `check_no_repeat_places`
3. `check_morning_slots`
4. `check_anchor_per_day`
5. `check_geo_coherence`

`passed = not errors` (warnings alone do not fail).

### D3 — Empty itinerary lock
`TripItinerary(days=[])` → `ValidationResult(passed=False, errors=["empty_itinerary"], warnings=[])`. Prefer this over the ambiguous earlier snippet comment in step4’s validation block; the clarified lock under step 4.7 wins.

Days that exist but have zero stops: treat as rule failures where applicable (e.g. no anchor) with day-index-specific messages — do not collapse to a single opaque error.

### D4 — Rule semantics (locked for implementer)

| Check | Fail when | Message style |
|-------|-----------|---------------|
| daily travel cap | `day.total_travel_min > MAX_DAILY_TRAVEL_MIN` | include day index |
| no repeat places | same `place.id` appears in more than one stop across the trip | include place id/name |
| morning slots | stop with `category in MORNING_ONLY_CATEGORIES` not in order ≤2 **or** `suggested_start_time > MORNING_SLOT_LATEST_START` | include day + place |
| anchor per day | no stop with `score > ANCHOR_MIN_SCORE` (strict `>`) | include day index |
| geo coherence | sample std-dev of stop coordinates (km) > `GEO_COHERENCE_MAX_STDDEV_KM` | include day index; **no magic number in function body** |

Geo coherence math: local km offsets from day centroid (`north ≈ Δlat×111`, `east ≈ Δlng×111×cos(lat)`); dispersion = `sqrt(sample_var(north) + sample_var(east))`. (Plain std-dev of distances-to-centroid is always 0 for any two-point day — rejected.) Days with <2 stops → skip coherence. Threshold constant only from `travel_rules`.

Dropped-stops warning text (exact token from step4):
`one_or_more_days_already_dropped_stops_prefer_expand_poi_search`

**Alternatives considered:** raise on invalid plans — rejected (Failure Boundary: return errors). Merge all rules into one function — rejected (blueprint Chain of Responsibility).

### D5 — Input shapes for DayPlan / TripItinerary
Pydantic models as in step4:
- `DayPlan(stops: list[ScheduledStop], total_travel_min: int, dropped_stops: list[DroppedStop] = [])`
- `TripItinerary(days: list[DayPlan])`
- `ValidationResult(passed: bool, warnings: list[str], errors: list[str])`

None itinerary → Pydantic/`TypeError` (programmer error), not a soft ValidationResult.

### D6 — OsrmRoutingProvider Adapter
`OsrmRoutingProvider.travel_matrix(waypoints)`:
- For every ordered pair `(i, j)` with `i != j`, call `await get_route([(lat_i, lng_i), (lat_j, lng_j)])`.
- Append `RouteLeg(from_place_id=id_i, to_place_id=id_j, duration_min=round(result.duration_min), distance_km=result.distance_km, used_fallback=result.fallback_used)`.
- Never import OSRM HTTP outside `geo/osrm`; this class is the only P4 module that imports `src.geo.osrm`.
- `get_route` already falls back — provider MUST NOT re-raise httpx for route miss.

**N=1 waypoint:** return `[]` (no pairs). **N=0:** return `[]`.

**Alternatives considered:** put adapter in `travel_engine/` — rejected (purity + Decision Log #6). Set graph state flag in P4 — deferred to P5.

### D7 — Tools envelope only
`ToolResult(ok, code, message, data)` in `schemas.py`. `execute_tool(name, input, ctx=None)`: if name not in a minimal registry dict (empty or placeholder keys without bodies), return `ToolResult(ok=False, code="unknown_tool", message=...)`. Never raise. Do not implement PHASE_TOOLS or tool impl modules beyond this envelope.

### D8 — Tests
- Validator: good fixture `errors=[]`; repeat place; late viewpoint; empty itinerary; dropped_stops → warning; Fake-built schedule preferred over network.
- Provider: mock `get_route` to assert pairwise call count and `used_fallback` mapping; optional live OSRM deferred to 4.10.
- execute_tool: unknown name → `ok=False`.
- After 4.8: PowerShell/`Select-String` purity under `src/travel_engine` still zero matches for geo/httpx.

## Risks / Trade-offs

- [Blueprint `state.used_osrm_fallback` vs step4 `RouteLeg.used_fallback`] → Mitigation: document in proposal/design; implement step4; wire state in P5.
- [O(n²) `get_route` calls for matrix] → Mitigation: accepted for P4 (N≤7 with base); no batch OSRM table API in scope.
- [Geo std-dev formula ambiguity] → Mitigation: document centroid + haversine distances sample std-dev in module docstring; constant from rules.
- [Anchor threshold `>` vs `>=`] → Mitigation: follow step4 docstring literally (`score > ANCHOR_MIN_SCORE`).
- [Stub planner tool files may have other placeholders] → Mitigation: extend in place; do not delete sibling stub tool modules.

## Migration Plan

1. Implement 4.7 → run step validation snippet + validator pytest.
2. Implement 4.8 → run envelope validation + provider/execute_tool tests + purity scan.
3. Update `docs/context.md` (4.7–4.8 ✅, Next = 4.9).
4. No DB migration; no deploy steps.

Rollback: revert the four module files to stubs; tests are additive.

## Open Questions

None blocking — empty-itinerary and fallback-flag locks are decided above. If implementer finds `ScheduledStop` lacking fields needed for a check, stop and ask rather than inventing parallel itinerary DTOs.
