## Context

P7.2–7.4 are done: TripService day surgery, four edit HTTP routes, and `tests/trips/test_edit_replan.py` (20 scenarios). `_persist_day_and_audit` already inserts one `TripEditEvent` then calls `EvaluationService.mark_trip_edited(trip.id)` before commit.

Today’s evaluation surface is the **thin** 7.2 shape:

- `EvaluationRepository.mark_user_edited(trip_id)` — select latest + set `user_edited=True` in one method
- `EvaluationService.mark_trip_edited(trip_id)` — delegates to that helper (no skip-if-already-edited branch)

Step **7.5** (`docs/steps/step7.md`) locks the polished API: split `get_latest_for_trip` / `mark_user_edited(evaluation)`, service no-ops when missing **or** already flagged, and explicit validation that the flag path never writes `trip_edit_events`.

Constraints: AGENT.md layering; evaluation reflects every edit (flag here, event in TripService); no new packages/migrations; no evaluation HTTP; flush-only repo writes.

## Goals / Non-Goals

**Goals:**

- Match step 7.5 repository/service signatures exactly.
- Keep flag update in the same UoW as TripPlaces + `TripEditEvent` (call site already correct).
- Prove: edit with eval → `user_edited` True; edit without eval → event + success; `mark_trip_edited` inserts zero edit events.
- Update `docs/context.md` (7.5 ✅, Next → 7.6).

**Non-Goals:**

- Evaluation HTTP routes
- New `TripEvaluation` columns / Alembic migrations
- Creating / updating `TripEditEvent` inside evaluation/
- Changing TripService edit semantics or edit HTTP
- Smoke / P7 close-out (7.6)

## Decisions

1. **Split repo helpers to match step7 signatures**
   - **Choice:** Replace combined `mark_user_edited(trip_id)` with:
     - `get_latest_for_trip(trip_id) -> TripEvaluation | None` (order by `created_at` desc, limit 1)
     - `mark_user_edited(evaluation: TripEvaluation) -> TripEvaluation` (set `user_edited=True`, flush only, return row)
   - **Why:** Step 7.5 locks this split; service owns the “missing / already true” policy.
   - **Alternatives:** Keep trip_id-based helper — rejected (diverges from SoT; harder to unit-test mutate-only).

2. **Service policy: no-op if missing or already `user_edited`**
   - **Choice:**
     ```python
     evaluation = await self.repo.get_latest_for_trip(trip_id)
     if evaluation is not None and not evaluation.user_edited:
         await self.repo.mark_user_edited(evaluation)
     ```
   - **Why:** Idempotent re-entry; avoids redundant flush; matches step docstring.
   - **Alternatives:** Always set True even if already True — harmless but not what step locks.

3. **TripService call site unchanged**
   - **Choice:** Keep `await EvaluationService(self.session).mark_trip_edited(trip.id)` after `insert_edit_event`, before `commit`. No signature change on the public method.
   - **Why:** 7.2 already wired the final name; 7.5 is evaluation-layer polish only.
   - **Alternatives:** Move flag write into TripRepository — rejected (cross-domain; AGENT evaluation ownership).

4. **Tests: focused evaluation + thin edit integration**
   - **Choice:** Prefer `tests/evaluation/test_mark_trip_edited.py` for unit/service scenarios (with/without row, already-edited skip, spy that `mark_trip_edited` does not insert `TripEditEvent`). Optionally assert one edit path in `test_edit_replan` sets `user_edited` when a seed evaluation exists — keep matrix lean.
   - **Why:** 7.4 suite has no evaluation assertions yet; dedicated file matches narrow 7.5 scope.
   - **Alternatives:** Only extend `test_edit_replan` — OK if fixtures already make seeding eval easy; still need a spy that isolates `mark_trip_edited` from TripService’s event insert.

5. **Latest evaluation = most recent `created_at` for `trip_id`**
   - **Choice:** Same query shape as today’s thin helper (`order_by created_at.desc().limit(1)`). Multiple eval rows for one trip are rare (generation append-only); flag the newest.
   - **Why:** Matches existing thin behavior and step “latest” wording.
   - **Alternatives:** Flag all evals for trip — out of scope / not in step.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Breaking callers of `mark_user_edited(trip_id)` | Grep + update; only evaluation service uses it today |
| Missing eval blocks edit | Service no-op; integration test without eval row |
| Accidental TripEditEvent in evaluation | Spy/assert zero inserts from `mark_trip_edited` alone; code review: no TripEditEvent imports in evaluation service |
| Already-edited skip hides bugs if wrong row selected | `get_latest_for_trip` + seed two rows in a unit test if needed |
| Context.md claims evaluation HTTP done | Explicit stubs note: HTTP still stub |

## Migration Plan

- No Alembic migration; `user_edited` column already exists on `trip_evaluations`.
- Deploy = ship code; rollback = revert evaluation repo/service + tests.
- Existing edit HTTP behavior unchanged except reliable `user_edited` when an evaluation row is present.

## Open Questions

- None blocking. If apply finds other callers of the old `mark_user_edited(trip_id)` signature, update them in the same change.
