## Context

P7.0–7.5 are implemented and recorded in `docs/context.md` (Next → 7.6). Day surgery, four edit HTTP routes, user-keyed `rate_limit_trip_edit`, `tests/trips/test_edit_replan.py` (20 scenarios), and flag-only `EvaluationService.mark_trip_edited` are real. No `scripts/test_p7_smoke.py` yet. Context still says “P7 in progress” / “7.6 smoke/context close-out remaining.”

Step **7.6** (`docs/steps/step7.md`) is documentation + verification close-out: optional smoke, import guards, full pytest, then stamp context P7-complete. SoT: blueprint v6.1 product; `step7.md` build contract; AGENT.md layering (no planner/LLM on edit path).

Constraints: no new packages; no production API changes expected; failed pytest → context.md unchanged; do not start F1 or mark production-readiness roadmap items done.

## Goals / Non-Goals

**Goals:**

- Prove P7 ship criteria remain green via `test_edit_replan` + full suite.
- Optional offline-first `scripts/test_p7_smoke.py` (owned trip, reorder day 1, one `TripEditEvent`, GeoJSON polyline when present).
- Spot-check edit-path import guards (no litellm / langgraph / PlannerService / execute_tool / redis in trips edit modules).
- Stamp `docs/context.md` only after green: Progress 7.0–7.6 ✅, Next → post-P7 / production readiness, modules + live edit endpoints + last-write-wins MVP note; clear P7 stub wording; keep evaluation HTTP stub.

**Non-Goals:**

- F1 chat replan / agent REPLAN HTTP
- New edit endpoints or TripService semantics
- Evaluation HTTP routes
- Marking wandr-backend-roadmap / production items done
- New packages or Alembic migrations
- Mandatory developer-manual rewrite in this change (follow-up OK per phase-end cadence)

## Decisions

1. **Smoke is optional but gated if present**
   - **Choice:** Prefer writing `scripts/test_p7_smoke.py` for parity with P1/P2/P4/P6, but step 7.6 allows skipping. If the file exists (or is added in this change), it MUST pass before the context stamp. If intentionally omitted, pytest + import guards alone unblock context.
   - **Why:** Step text marks smoke “optional”; failure boundary is “do not update context.md if tests fail.”
   - **Alternatives:** Always require smoke — rejected (diverges from SoT optional wording). Never write smoke — weaker live proof vs prior phases.

2. **Offline Fake preferred; live OSRM behind env flag**
   - **Choice:** Default path uses Fake/`RoutingProvider` doubles already used in edit tests (or ASGI + DI override). Live OSRM only when an explicit env flag is set (mirror `OPTIONAL_LIVE_OSRM` / P4–P6 pattern). Fail-fast sections; non-zero exit on failure.
   - **Why:** Step locks “Offline Fake preferred; live OSRM optional behind env flag.” Keeps CI/dev green without public OSRM.
   - **Alternatives:** Always hit live OSRM — rejected (flaky; contradicts step).

3. **Minimal smoke sections (not a second pytest suite)**
   - **Choice:** At least: (1) seed/load owned trip with ≥2 stops on day 1; (2) `PATCH .../stops/reorder`; (3) assert exactly one `TripEditEvent` for that edit; (4) `GET .../geojson` — LineString / polyline present when trip places have polylines; (5) import guards for trips edit modules. Do not re-assert the full 20-scenario matrix.
   - **Why:** Step lists those proofs; `test_edit_replan` already owns depth.
   - **Alternatives:** Full HTTP matrix in smoke — duplicate of 7.4; skip GeoJSON — weak vs ship criteria table.

4. **Import guards: trips edit surface only**
   - **Choice:** Scan `src/trips/` modules on the edit path (`service.py`, `router.py`, `dependencies.py`, related helpers) for forbidden imports: `litellm`, `langgraph`, `PlannerService`, `execute_tool`, `redis`. Use the same fail-fast style as `scripts/test_p6_smoke.py` section 6 / existing purity tests if already present — do not invent broader redis bans already covered by P6 unless gaps appear.
   - **Why:** Step 7.6 import-guard list is edit-path specific.
   - **Alternatives:** Whole-`src` scan — out of scope / noisy.

5. **Context stamp content locked to step 7.6 bullets**
   - **Choice:** Update only after green:
     - Last updated = apply day; Phase = P7 complete (or equivalent); Next = post-P7 / production readiness
     - Progress rows 7.0–7.6 ✅
     - Current state one-liner per step
     - Implemented modules: edit methods, routes, `rate_limit_trip_edit`, `mark_trip_edited`, `populate_leg_polylines`, preserve-order schedule
     - Live endpoints: four edit rows (already listed — confirm accurate)
     - Known MVP limitation: concurrent edits last-write-wins
     - Stubs: remove “P7 trip edit/replan still stubs”; keep evaluation HTTP stub; do not claim evaluation HTTP done
   - **Why:** Matches step UPDATE block + `.cursorrules` context maintenance.
   - **Alternatives:** Stamp mid-apply — forbidden. Claim F1/production done — forbidden by DO NOT.

6. **No product code unless smoke or guards force a tiny fix**
   - **Choice:** This change is verification + docs. If pytest reveals a regression, fix the minimal bug under existing P7 locks (amend `step7.md` first only if a lock conflicts with reality). Do not expand scope into F1.
   - **Why:** 7.6 is close-out, not a new feature batch.
   - **Alternatives:** Bundle unrelated polish — rejected.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Premature context stamp | Tasks order: pytest (+ smoke if present) → then context; failure path leaves context untouched |
| Smoke flakes on live OSRM | Default Fake/offline; live behind flag |
| Smoke duplicates pytest | Keep smoke to reorder + event + GeoJSON + guards |
| Over-claim evaluation HTTP / production readiness | Explicit stubs + DO NOT in tasks |
| Skipping smoke leaves weaker live proof | Document in context Scripts line if smoke omitted; pytest remains mandatory |
| Import guard false positives on comments | Match import-line patterns like P6 smoke (`import`/`from` at line start) |

## Migration Plan

- No Alembic migration; no package changes; no endpoint changes expected.
- Deploy = ship optional smoke script + updated `docs/context.md` after green.
- Rollback = revert context.md / delete smoke script; production API unchanged.

## Open Questions

- None blocking. Apply may choose to omit smoke if time-boxed; if omitted, note absence in the apply summary and still stamp context after pytest + import-guard spot-check pass.
