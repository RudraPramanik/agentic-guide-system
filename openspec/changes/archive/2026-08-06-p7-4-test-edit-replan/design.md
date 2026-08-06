## Context

P7.0–7.3 are done: base prefs, shared `populate_leg_polylines`, TripService day surgery + Fake ops tests (`tests/trips/test_trip_edit_ops.py`), four edit HTTP routes + thin auth/429/would-drop HTTP (`tests/trips/test_trip_edit_http.py`). `docs/context.md` Next = **7.4**.

Step **7.4** (`docs/steps/step7.md`) requires `tests/trips/test_edit_replan.py` covering **20 locked scenarios** (v2.1 regressions included). Behavior SoT remains `openspec/specs/p7-trip-edit-replan` + step7; this step is verification, not new product surface.

Constraints: AGENT.md; FakeRoutingProvider only (no live OSRM/LLM); `wandr_test` + existing trips fixtures; prefer service-level + thin HTTP for ownership/rate limit; zero new packages.

## Goals / Non-Goals

**Goals:**

- Green `tests/trips/test_edit_replan.py` covering all 20 step-7.4 scenarios.
- Explicit rollback assertion: failed add → `TripEditEvent` count unchanged.
- Full suite remains green (`pytest tests/ -v`).
- Context checkpoint → Next **7.5**.

**Non-Goals:**

- Evaluation polish (7.5) / smoke + final context (7.6)
- Changing edit algorithms, schemas, or routes unless a test proves a lock violation (amend step7 first)
- Deleting 7.2/7.3 thin test modules (may overlap; keep both unless consolidating helpers only)
- Live OSRM / network in CI unit tests

## Decisions

1. **New module `test_edit_replan.py` is the SoT suite name**
   - **Choice:** Create the file named in step 7.4 even though `test_trip_edit_ops.py` / `test_trip_edit_http.py` already exist. Put the full matrix here; reuse seed/Fake/limiter helpers by importing private helpers **or** duplicating small local seeds (prefer shared local helpers / copy patterns — do not invent a new `conftest` package unless duplication hurts).
   - **Why:** Step validation command is `pytest tests/trips/test_edit_replan.py -v`.
   - **Alternatives:** Rename/move ops+http into `test_edit_replan.py` only — optional cleanup; not required if matrix is complete in the new file.

2. **Service-first, HTTP-thin split**
   - **Choice:** Scenarios about order/polylines/dropped_stops/morning-slot/rollback/audit/routing-spy → call `TripService` with `FakeRoutingProvider` (and optionally spy call counts). Ownership 403 + rate-limit 429 → HTTP via ASGI client + patterns from `test_trip_edit_http.py` (`use_fake_routing` monkeypatch, keyed limiter mock).
   - **Why:** Step lock: “Prefer service-level tests + thin HTTP for auth + rate limit.”
   - **Alternatives:** All-HTTP matrix — slower, harder to spy RoutingProvider, still OK for a few cases.

3. **FakeRoutingProvider for drop / OSRM-fallback cases**
   - **Choice:** Force `dropped_stops` via high `default_duration_min` (already used in 7.2/7.3). OSRM-fallback case: Fake returns `None` polyline / fallback durations so success is 200 without live OSRM.
   - **Why:** Offline CI; matches existing Fake API.
   - **Alternatives:** Mock `OsrmRoutingProvider` — unnecessary if Fake covers the contract.

4. **Morning-slot asymmetry fixtures**
   - **Choice:** Seed a day with a morning-only category place mid-list; reorder → expect 200 + warnings + commit; remove/add/reoptimize with the same morning violation → 422 (no downgrade).
   - **Why:** v2.1 locks #21 / scenarios 14–15.
   - **Alternatives:** Patch `validate_trip` — rejected (tests must exercise real preserve-order + validator strings).

5. **Multi-day routing spy**
   - **Choice:** Seed ≥2 days; edit day 1 only; assert Fake `travel_matrix` / `route_polyline` call counts reflect only the mutated day (unchanged days from stored TripPlace fields).
   - **Why:** Lock #20 / scenario 19.
   - **Alternatives:** Assert no DB coords reload — weaker; spy is the step requirement.

6. **Audit exactly-one + rollback**
   - **Choice:** Count `TripEditEvent` before/after success (delta == 1) and after failed add/reoptimize (delta == 0). Prefer DB query over relying on response alone.
   - **Why:** Locks #13/#16; step failure path.
   - **Alternatives:** Only check HTTP status — insufficient per step.

7. **Do not change product code unless red**
   - **Choice:** If a scenario fails against locked behavior, fix the minimal product bug (or amend step7 if the lock is wrong), then re-green tests. Do not weaken assertions to match buggy code.
   - **Why:** 7.4 is the verification gate for 7.2–7.3.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Overlap with `test_trip_edit_ops` / `test_trip_edit_http` slows suite | Accept overlap for step naming SoT; optional later consolidate helpers only |
| Flaky rate-limit if real window used | Mock/override limiter like 7.3 |
| Morning-slot fixture hard to construct | Use known morning-only category from `travel_rules`; assert via validator prefix |
| Spy brittle if Fake call shape changes | Spy at Fake method level; document expected call budget loosely (≥1 for mutated day, 0 matrix for other days’ places) |
| Accidental live OSRM | Never construct `OsrmRoutingProvider` in this module; inject Fake always |

## Migration Plan

- Tests-only deploy impact: none.
- Rollback: delete/revert `test_edit_replan.py` + context Next step.
- No Alembic / no config defaults required for green path.

## Open Questions

- None blocking — if preserve-order morning fixture needs a specific Place category string, take it from `travel_rules` constants already used in travel_engine tests.
