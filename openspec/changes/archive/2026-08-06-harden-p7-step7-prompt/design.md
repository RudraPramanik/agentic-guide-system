## Context

P6 is green. `design-p7-edit-replan` authored v1 `docs/steps/step7.md` (and related delta specs). Critic review (`docs/step7_critics.md`) plus codebase verification found: (1) a hard contradiction on who creates `TripEditEvent`, (2) silent `dropped_stops` on add/reoptimize, (3) ambiguous efficiency and permutation wording, (4) a flawed shared-helper proposal that would collapse `OptimizeResult.legs` to consecutive-only (breaking morning-extract hops), (5) invented DayPlan polyline fields that do not exist on `ScheduledStop`/`DayPlan`, and (6) neither draft locked reorder vs `build_day_schedule`’s `_extract_morning_first`.

This change updates the **build contract only** (`step7.md` + OpenSpec deltas). Application code lands in later implementation applies, guided by the hardened SoT.

## Goals / Non-Goals

**Goals:**
- Make `docs/steps/step7.md` the single P7 implementation SoT (v2.1).
- Lock accepted critic fixes + corrected solutions so implementers do not re-litigate.
- Align delta specs with v2.1 so archive/sync does not resurrect v1 contradictions.
- Keep prompt style consistent with `step5.md` / `step6.md` (Decision Log, FAILURE BOUNDARY, ✅ proofs).

**Non-Goals:**
- Implementing TripService edit methods, routes, or tests in this change.
- Chat/LLM full-trip replan; evaluation HTTP; row-level locking; Alembic for base coords.
- Changing generation-time morning extract behavior for planner/tools.
- Treating `docs/step7_critics.md` as the build contract (historical review only).

## Decisions

### D1 — TripEditEvent ownership → TripService
- **Choice:** `TripRepository.insert_edit_event` / TripService UoW creates exactly one `TripEditEvent` per successful edit. `EvaluationService.mark_trip_edited(trip_id)` only flips `user_edited` when a `TripEvaluation` exists.
- **Why:** Model lives in `trips/`; v1 contradicted itself; avoids double-insert.
- **Alternatives:** Blueprint’s `record_edit()` creates the event — rejected for domain ownership clarity; rename documents the blueprint delta.
- **AGENT.md:** Still satisfied — evaluation is notified on every edit in the same UoW.

### D2 — Shared geometry without regressing optimize_route
- **Choice:** Extract/promote a helper used for **polyline population** (and optionally consecutive-leg extraction for fixed-order callers). `optimize_route` MUST keep `legs = full pairwise matrix`. Reorder path: `travel_matrix` once → consecutive chain for user’s order → shared polyline helper — **no** permutation search.
- **Why:** Critics’ `compute_legs_and_polylines` that replaces `OptimizeResult.legs` with consecutive-only would break `build_day_schedule` morning-extract hop lookups.
- **Name in prompt:** Prefer `populate_leg_polylines` (promote `_populate_polylines`) plus thin `_fixed_order_day` in TripService; optional `compute_fixed_order_geometry` that returns `(consecutive_legs, leg_polylines, day_polyline)` **without** being wired as OptimizeResult.legs.
- **Alternatives:** Duplicate polyline loops in TripService — rejected (drift); full matrix+polyline mega-helper that overwrites optimize legs — rejected.

### D3 — Polyline persist path (no DayPlan field invention)
- **Choice:** Keep `leg_polylines: list[str | None]` parallel to the scheduled stops; on persist, zip into `TripPlace.polyline`. Do **not** add `leg_polyline` to `ScheduledStop` or `day_polyline` to `DayPlan` in P7.
- **Why:** Generation already maps schedule dict `leg_polyline` → column; models have no those fields today.
- **Alternatives:** Extend P4 models — speculative, out of scope.

### D4 — Reorder preserve-order schedule + morning-slot downgrade
- **Choice:** Add `build_day_schedule_preserve_order(...)` (or `build_day_schedule(..., *, preserve_order: bool = False)`) that **skips** `_extract_morning_first`. REORDER uses preserve-order. Other edit types use existing `build_day_schedule` (morning extract OK after optimize). On REORDER only, `morning_slot_violation` errors from `validate_trip` are downgraded to warnings (commit proceeds). Prefer prefixing morning-slot error strings with `morning_slot_violation:` for reliable filter (small P4-compatible string tweak).
- **Why:** Without this, “preserve user order” is false; morning downgrade alone is incoherent.
- **Alternatives:** Accept morning extract on reorder — rejected (defeats feature); skip validate on reorder — rejected.

### D5 — No silent drops on add/reoptimize
- **Choice:** If `optimize_route` returns non-empty `dropped_stops` → `TripEditValidationError` code `edit_would_drop_other_stops`, details list would-drop, rollback. Document `still_over_budget` with empty drops (single over-budget stop) → normally fails travel-cap validate.
- **Why:** Unrequested side-effect on a saved trip.

### D6 — Unchanged days = zero network
- **Choice:** `_validate_full_trip` rebuilds other days entirely from stored TripPlace fields (`total_travel_min = sum(travel_time_min)`); only mutated day may call RoutingProvider.
- **Why:** Closes “recompute lightly” ambiguity.

### D7 — Precise locks from critics (accepted as-is)
- Permutation: `len(ids)==len(current) and set(ids)==set(current)`.
- Missing stop on day: 404 `stop_not_found_on_day`.
- Concurrency: documented MVP last-write-wins (forward lock for row locking).
- User-keyed `rate_limit_trip_edit` dependency (settings `RATE_LIMIT_TRIP_EDIT_*`); raise `WandrError`/`RateLimitedError` with 429 — exception may need adding (does not exist today). Do not put UUID paths in `_route_limit_table`. Middleware IP default may still apply — document dual limit.

### D8 — Prompt substep order 7.0–7.6
| Step | Deliverable |
|------|-------------|
| 7.0 | base_lat/lng in preferences + `_resolve_base` |
| 7.1 | Shared polyline / fixed-order geometry helper (safe vs full matrix) |
| 7.2 | TripService edit ops + schemas/exceptions |
| 7.3 | Four router endpoints + user-keyed rate limit |
| 7.4 | `tests/trips/test_edit_replan.py` (incl. v2.1 regressions) |
| 7.5 | `mark_trip_edited` |
| 7.6 | Optional smoke + `context.md` |

### D9 — Layering unchanged
No `PlannerService` / `execute_tool` / LangGraph / LLM on edit path. Blueprint “tools” wording = algorithms, not TOOL_REGISTRY.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Blueprint still says `record_edit` writes TripEditEvent | Decision Log + step7 header call out intentional delta; sync blueprint later if desired |
| Preserve-order + morning warnings may leave awkward times | Accept for MVP; user chose order |
| Dual IP + user rate limits | Document; fail-open on limiter backend errors |
| Hydration score=1.0 masks real anchors | Document MVP; ANCHOR_MIN_SCORE=0.7 still passes |
| Implementers follow critics file instead of step7 | Header: critics = historical; step7.md = SoT |
| Future code apply invents DayPlan polyline fields | Explicit DO NOT in 7.2 |

## Migration Plan

1. Apply this change → rewrite `docs/steps/step7.md` to v2.1; delta specs land under this change.
2. Do **not** update `docs/context.md` Progress until code ship (7.6).
3. Implementation: separate OpenSpec applies `7.0`→`7.6` (minimal replan only when feature reality conflicts with a lock — prefer amending step7 then code).
4. Archive/sync this change (and eventually `design-p7-edit-replan`) so main specs match v2.1.
5. Rollback: revert `step7.md` + this change folder; no runtime impact (docs-only).

## Open Questions

None blocking. Product defaults locked above:
- Reorder = preserve-order schedule.
- Evaluation = flag-only `mark_trip_edited`.
- Geometry share = polylines (+ fixed-order consecutive), not OptimizeResult.legs overwrite.
