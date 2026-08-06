## Why

P7.2–7.3 shipped TripService day surgery and the four edit HTTP routes (auth + user-keyed rate limit), but coverage is still thin: Fake service tests from 7.2 and OpenAPI/auth/429 smoke from 7.3. Step **7.4** (`docs/steps/step7.md`) is the locked verification batch — without `tests/trips/test_edit_replan.py` covering the full v2.1 matrix (preserve-order, dropped_stops rollback, morning-slot downgrade asymmetry, mutated-day-only routing, audit count, 429), regressions can slip past CI before 7.5–7.6.

## What Changes

- Create `tests/trips/test_edit_replan.py` with the **20 required scenarios** from step 7.4 (service-level preferred + thin HTTP for ownership / rate limit).
- Use `FakeRoutingProvider` (and existing `wandr_test` / trips fixtures); no live OSRM or LLM.
- Prove rollback failure path: failed add → `TripEditEvent` count unchanged.
- Keep 7.3 thin HTTP tests; expand coverage here rather than rewriting product code unless a lock conflict appears.
- Update `docs/context.md` after green (Progress 7.4 ✅, Next → 7.5; note full edit/replan pytest landed).

**Non-goals:** Evaluation polish / full `mark_trip_edited` linkage (7.5); smoke script / P7 context cadence close-out (7.6); changing TripService edit semantics or router surface; live OSRM in CI; new packages/migrations; PlannerService / `execute_tool` / LLM on edit path; chat “replan whole trip” (F1).

**Naming note:** Blueprint Phase P7 labels this suite as “7.3”; `docs/steps/step7.md` v2.1 expands P7 to **7.0–7.6** with this work as **7.4**. Build and verify from the step contract; product behavior remains `openspec/specs/p7-trip-edit-replan` + blueprint Edit & Replan table.

## Capabilities

### New Capabilities

- `p7-edit-replan-tests`: Pytest contract for P7 edit/replan — `tests/trips/test_edit_replan.py` MUST cover the step 7.4 scenario matrix with FakeRoutingProvider, assert rollback/audit/v2.1 regressions, and stay offline (no live OSRM/LLM).

### Modified Capabilities

- `p7-trip-edit-replan`: Add an explicit verification-gate requirement that the behavior contract is proven by the 7.4 suite (not only by thin 7.3 HTTP smoke).

## Impact

- **Code:** primarily `tests/trips/test_edit_replan.py` (+ reuse of Fake routing, trips seed helpers, limiter mock patterns from `test_trip_edit_http.py`); product modules only if a test reveals a lock violation (amend `docs/steps/step7.md` first).
- **Docs:** `docs/context.md` after validation (Next → 7.5).
- **AGENT.md:** tests must not import/call litellm/PlannerService on the edit path under test; Fake only.
- **Depends on:** P7.2 service ops + P7.3 four routes + `rate_limit_trip_edit`.
- **Unlocks:** 7.5 evaluation polish; 7.6 smoke + context close-out.
- **No DB migration / no new packages / no new live endpoints.**
