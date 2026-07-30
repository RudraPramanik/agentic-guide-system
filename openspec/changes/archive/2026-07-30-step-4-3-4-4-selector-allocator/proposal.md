## Why

P4.0–4.2 are done (`protocols`, `travel_rules`, CORS). The next locked batch in `docs/steps/step4.md` is **4.3–4.4**: score/filter candidates (`place_selector`) and split them into per-day lists (`day_allocator`). These pure modules unblock route optimization (4.5+) and need focused unit tests now so 4.9 is expansion, not discovery.

## What Changes

- **4.3** — Replace stub `src/travel_engine/place_selector.py` with `PlaceCandidate`, `TripPreferences`, `ScoredPlace`, `score_place`, `explain_selection`, and `select_places` (sum-of-weights scoring + greedy `AVOID_SAME_DAY_PAIRS` filter; budget soft-only).
- **4.4** — Replace stub `src/travel_engine/day_allocator.py` with `allocate_days` (caps, visit-time budget via `visit_duration_min`, local haversine clustering within `CLUSTER_RADIUS_KM`; `days < 1` → `ValueError`).
- Add focused pytest under `tests/travel_engine/` for selector + allocator (required cases from step 4.3/4.4 + 4.9 preview); run step ✅ validation snippets.
- Update `docs/context.md` Progress for 4.3–4.4 only (Next step → 4.5); do **not** claim full P4 complete.

**Non-goals:** No edits to `step4.md` / `step4-fix.md` / blueprint; no route_optimizer / schedule / validator (4.5–4.7); no planner adapter (4.8); no full P4 pytest plan / smoke (4.9–4.10); no HTTP routers; no SQLAlchemy Place imports; do not apply stale `openspec/changes/p4-travel-engine` tasks.

**Source of truth:** Implement from `docs/steps/step4.md` steps 4.3–4.4. `docs/steps/step4-fix.md` is already absorbed into step4’s Decision/Fix Log — consult only if a lock’s *rationale* is unclear; do not re-open design from the fix addendum.

## Capabilities

### New Capabilities

- `travel-engine-place-selector`: Pure score + filter API for candidate places (sum weights, conflict filter, explain strings).
- `travel-engine-day-allocator`: Pure day packing under place caps, visit budget, and geo pre-clustering.

### Modified Capabilities

<!-- Intentionally empty — umbrella `p4-travel-engine-layer` already states these requirements; this change implements them via focused specs. -->

## Impact

- **Code:** `src/travel_engine/place_selector.py`, `src/travel_engine/day_allocator.py` (stubs → real); reads `travel_rules` only.
- **AGENT.md:** travel_engine purity (no geo/LLM/DB/httpx); haversine math local to allocator only.
- **Docs:** `docs/context.md` incremental progress only.
- **Tests:** `tests/travel_engine/test_place_selector.py`, `tests/travel_engine/test_day_allocator.py` (+ shared fixtures if useful); step validation snippets; purity still zero geo imports.
- **Build contract:** Exact APIs/behaviors from `docs/steps/step4.md` 4.3–4.4.
