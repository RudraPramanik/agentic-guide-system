## Context

P6 complete. `docs/steps/step7.md` v2.1 is the P7 SoT. `save_from_state` today builds preferences from interests/budget/include_* only — no base coords. Destination already has `lat`/`lng`. No edit HTTP yet. This change is **only** step 7.0: persist + resolve helper + tests + context bump.

**Preflight (apply must confirm before coding):** P6.5 green in `docs/context.md`; `route_polyline` real; implement from §7.0 only — do not start 7.1+.

## Goals / Non-Goals

**Goals:**
- Persist generation base into `Trip.preferences` when present on state.
- Provide a safe `_resolve_base` for later edit ops (prefs → Destination).
- Prove with pytest; mark 7.0 ✅ in `docs/context.md`.

**Non-Goals:**
- Edit routes / TripService day surgery / polyline extract / preserve-order schedule.
- Alembic / new Trip columns (prefs JSON is enough — forward lock F4).
- Changing planner SSE, GeoJSON, or evaluation.

## Decisions

### D1 — Preferences JSON, not DB columns
- **Choice:** Store `base_lat`/`base_lng` inside existing `Trip.preferences` JSONB.
- **Why:** Step7 lock — no migration; matches PlanRequest/TravelState shape.
- **Alternatives:** Dedicated columns — deferred (F4).

### D2 — Presence and type rules
- **Choice:** Persist only when both values are present and coercible via `float(...)`. If either missing, omit both keys. In `_resolve_base`, accept `int`/`float` only (reject bool/str masquerading — `isinstance(..., (int, float))` and treat `bool` as missing since `bool` subclasses `int` in Python: **explicitly exclude `bool`**).
- **Why:** Avoid `True` → `1.0` lat; avoid half-written prefs.
- **Alternatives:** Persist one key if only one present — rejected (incomplete origin).

### D3 — Helper placement
- **Choice:** Module-private or `TripService` method `_resolve_base(trip, destination)`. Pure sync; no I/O.
- **Why:** Edit preamble will call it; keep colocated with save.

### D4 — String numeric values
- **Choice:** On **save**, if state has string numbers, `float()` may succeed — persist floats. On **resolve**, only `int`/`float` (non-bool) win; strings in prefs → destination fallback.
- **Why:** State from planner is typically float; legacy/corrupt prefs stay fail-soft.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Pre-7.0 trips lack base prefs | Documented MVP — resolve uses Destination centroid |
| Destination far from true hotel base | Same as generation fallback; F4 if painful |
| Agents implement 7.1 in same apply | Tasks scoped to 7.0 only; DO NOT list in tasks |

## Migration Plan

1. Apply code + tests.
2. Update `docs/context.md` (7.0 ✅, Next = 7.1).
3. No DB migration; rollback = revert service + tests.
4. Next OpenSpec change: `p7-1-…` for shared polyline helper.

## Open Questions

None — locked by `docs/steps/step7.md` §7.0.
