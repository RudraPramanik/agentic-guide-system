## Context

Implement P4 steps **4.3–4.4** from the locked build contract `docs/steps/step4.md`. Planner SoT remains `docs/blueprint_final.md` v6.1. Do **not** revise step4, step4-fix, or the blueprint in this change.

**Already shipped:** `travel_rules.py` (structural vs interest vocab, caps, `visit_duration_min`, `AVOID_SAME_DAY_PAIRS`, `CLUSTER_RADIUS_KM`, `ACTIVE_DAY_VISIT_BUDGET_MIN`, `MAX_PLACES_PER_DAY`) and `protocols.py`. Stubs remain: `place_selector.py`, `day_allocator.py` (~1-line placeholders).

**Doc guidance:** Use `step4.md` as the only implementation contract. `step4-fix.md` locks are already merged into step4’s Decision/Fix Log (sum scoring, `.get` durations, vocabulary split) — no parallel design from the fix addendum.

## Goals / Non-Goals

**Goals:**
- Ship `place_selector` (4.3) and `day_allocator` (4.4) exactly per step4 prompts.
- Pass each step’s ✅ validation; keep travel_engine pure (local haversine only — no `src.geo`).
- Land focused pytest for both modules covering step 4.9 ★ cases for selector/allocator.
- Bump `docs/context.md` for 4.3–4.4 only; Next step = 4.5.

**Non-Goals:**
- Steps 4.5–4.10 (optimizer, schedule, validator, adapter, full suite, smoke).
- Morning-only enforcement (schedule_builder + validator).
- HTTP, DB mapping from SQLAlchemy `Place`, or planner tools.
- Continuing or applying stale `openspec/changes/p4-travel-engine`.

## Decisions

### D1 — Build contract is step4.md only
Copy types/APIs from steps 4.3–4.4. Types live in `place_selector.py` (or a tiny shared types module if cleaner — prefer colocating on selector since allocator imports `ScoredPlace` from there). No SQLAlchemy models.

### D2 — Scoring is sum, never max/avg
```
score = sum(CATEGORY_WEIGHTS[tag] for tag in place.enriched_tags
            if tag in CATEGORY_WEIGHTS and tag in interests)
```
Unknown tags contribute 0. Empty `enriched_tags` / empty interests → score 0, still returned. `score_breakdown` maps contributing tag → weight.

### D3 — AVOID_SAME_DAY_PAIRS: greedy keep-higher-score
Document in module docstring (locked):
1. Score all candidates; sort descending by score, stable tie-break by `(name, id)`.
2. Walk sorted list; maintain accepted set.
3. For each candidate, if pairing its `category` with any already-accepted place’s category forms a forbidden pair (unordered match against `AVOID_SAME_DAY_PAIRS`, including same-category pairs like monastery–monastery), **skip** (drop) the lower-scored candidate — i.e. do not add the current one when it conflicts with a higher-scored already-kept place.
4. Budget never hard-excludes.

This is selection-time filtering of the eventual day *pool*; per-day pair enforcement beyond this is not required in 4.3.

### D4 — explain_selection is a compact string
Format like `"Tiger Hill score=2.6 [photography=1.4, viewpoint=1.2]"`. Trace-shaped only — not a DB column.

### D5 — Day allocation: cluster-first then pack by score
Locked algorithm for `allocate_days`:
1. If `days < 1`: raise `ValueError("days must be >= 1")`.
2. Pure-Python haversine helper local to the module; distance vs `CLUSTER_RADIUS_KM` (no `src.geo`).
3. Build clusters: greedy — walk places by descending score; assign each place to the first existing cluster whose centroid (or first member) is within radius, else start a new cluster.
4. Assign clusters to days preferring underfilled days (round-robin / load-balance by current place count), then pack members into day lists while respecting `MAX_PLACES_PER_DAY` and `sum(visit_duration_min(category)) <= ACTIVE_DAY_VISIT_BUDGET_MIN`. Higher scores win when a day cannot take everyone.
5. Return exactly `days` lists (some may be empty if not enough places). Overflow that cannot fit any day is omitted (document in docstring).
6. Always use `visit_duration_min()` — never bare duration dict subscript.

### D6 — Tests land with this batch
Create `tests/travel_engine/test_place_selector.py` and `test_day_allocator.py` now with the ★ cases from step 4.9 that apply to these modules. Full purity/CORS/optimizer suites remain 4.9.

## Risks / Trade-offs

- [Risk] Ambiguous cluster packing order could fail the 18/3 fixture → Mitigation: implement D5 explicitly; validation asserts len==3, ≤6/day, visit budget; tune only if assertions fail while staying within locks.
- [Risk] Conflict filter interpreted as per-day instead of pool filter → Mitigation: D3 + docstring + test with two monasteries both in candidate list → only higher-scored kept.
- [Trade-off] Full travel_engine pytest tree waits for 4.9 → Acceptable; this batch owns selector/allocator files so 4.9 extends rather than invents.
- [Risk] Accidental `src.geo` import for haversine → Mitigation: local math only; purity scan in closeout.

## Migration Plan

1. Implement 4.3 place_selector + step validation + pytest  
2. Implement 4.4 day_allocator + step validation + pytest  
3. Update context.md progress  
4. Rollback: revert the two modules + tests; stubs can be restored

## Open Questions

None — step4 locks + D3/D5 greedy rules are sufficient for apply.
