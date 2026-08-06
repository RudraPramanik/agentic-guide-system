## ADDED Requirements

### Requirement: Optional P7 smoke script
The project MAY provide `scripts/test_p7_smoke.py`. IF the script is present (or added in this change), it MUST exercise at least:

1. an owned trip with day-1 stops available for reorder
2. reorder of day 1 via the edit HTTP path (or equivalent service path used by smoke)
3. assertion that exactly one `TripEditEvent` exists for that edit
4. `GET /api/v1/trips/{id}/geojson` reflecting polyline / LineString geometry when polylines are present on trip places
5. import guards for trips edit modules (MUST NOT import `litellm`, `langgraph`, `PlannerService`, `execute_tool`, or `redis`)

Smoke MUST prefer an offline Fake / injected `RoutingProvider` path. Live OSRM MUST be optional behind an explicit env flag. Smoke MUST exit non-zero on any failed section.

#### Scenario: Smoke fails closed when present
- **WHEN** `scripts/test_p7_smoke.py` exists and any section fails
- **THEN** the script exits non-zero and P7 MUST NOT be marked complete in `docs/context.md`

#### Scenario: Offline Fake is the default smoke path
- **WHEN** smoke runs without the live-OSRM env flag
- **THEN** it completes without requiring a live OSRM network call for the reorder proof

#### Scenario: Smoke omitted is allowed
- **WHEN** apply intentionally omits `scripts/test_p7_smoke.py`
- **THEN** P7 may still be stamped complete after pytest and import-guard spot-checks pass

### Requirement: Edit-path import guards
Trips edit modules (`src/trips` edit surface: service, router, dependencies, and related edit helpers) MUST NOT import `litellm`, `langgraph`, `PlannerService`, `execute_tool`, or `redis`. Agents MUST spot-check these guards during the 7.6 apply (via smoke section and/or equivalent static scan).

#### Scenario: Forbidden planner/LLM imports blocked
- **WHEN** import guards are scanned on trips edit modules
- **THEN** no matching `import`/`from` of `litellm`, `langgraph`, `PlannerService`, or `execute_tool` is present

#### Scenario: Redis not imported in trips edit modules
- **WHEN** import guards are scanned on trips edit modules
- **THEN** no matching `import`/`from` of `redis` is present (rate limiting uses the shared limiter DI, not direct redis clients in trips)

### Requirement: Pytest green before context stamp
Before updating `docs/context.md` to claim P7 complete, the apply session MUST run and pass:

- `python -m pytest tests/trips/test_edit_replan.py -v`
- `python -m pytest tests/ -v`

#### Scenario: Edit-replan suite passes
- **WHEN** `python -m pytest tests/trips/test_edit_replan.py -v` runs in the apply session
- **THEN** all tests pass

#### Scenario: Full suite passes
- **WHEN** `python -m pytest tests/ -v` runs in the apply session
- **THEN** all tests pass

#### Scenario: Failed pytest blocks context stamp
- **WHEN** either pytest command fails
- **THEN** agents MUST NOT update `docs/context.md` to mark P7 complete

### Requirement: Context stamp only after green
After required pytest (and smoke if present) succeed, `docs/context.md` MUST be updated to:

- Last updated = apply day; Next step → post-P7 / production readiness
- Progress **7.0–7.6** ✅
- Current state: P7 done — day edit/replan HTTP + `TripEditEvent`; shared polyline helper; preserve-order reorder
- Implemented modules note edit methods, routes, `rate_limit_trip_edit`, `mark_trip_edited`, `populate_leg_polylines`, preserve-order schedule
- Live endpoints include the four day-edit routes
- Known MVP limitation: concurrent edits last-write-wins
- Stubs: remove wording that P7 trip edit/replan HTTP is still stub; MUST NOT claim evaluation HTTP done

The update MUST NOT mark F1 chat replan or roadmap production-readiness items as done.

#### Scenario: Premature stamp forbidden
- **WHEN** pytest has not passed (or smoke is present and has not passed) in the apply session
- **THEN** agents MUST NOT mark P7 complete in `docs/context.md`

#### Scenario: Full suite and optional smoke pass before context stamp
- **WHEN** required pytest succeeds and smoke (if present) succeeds
- **THEN** `docs/context.md` may mark Progress 7.0–7.6 ✅ and set Next → post-P7 / production readiness

#### Scenario: Evaluation HTTP remains stub
- **WHEN** `docs/context.md` is updated for P7 complete
- **THEN** evaluation HTTP is still listed as stub / not done
