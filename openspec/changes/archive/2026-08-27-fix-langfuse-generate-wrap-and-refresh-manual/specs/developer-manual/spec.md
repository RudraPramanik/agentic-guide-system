## ADDED Requirements

### Requirement: Manual refresh after P7 and post-P7/v7 catch-up
After P7 is recorded complete in `docs/context.md` and post-P7/v7 work through at least V6.1 is marked ✅ (CI, observability/token usage, golden harness, hybrid search as shipped in context), the developer manual MUST be refreshed in this change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to a marker that covers P7 complete plus the highest validated v7 step in context (e.g. **P7 + V6.1** or equivalent wording), bump **Last refreshed**, and update the snapshot so it no longer claims P7 trip edit/replan HTTP, P7 smoke, or shipped v7 modules (token usage / Langfuse facade, `scripts/run_evals.py`, hybrid/`places_v2` when ✅) are unbuilt. Residual stubs MUST still match context (evaluation HTTP; `auth/dependencies.py`; deferred V6.2/V6.3 if still deferred). The maintenance refresh log MUST record a catch-up row for this through-step.

#### Scenario: Index reflects P7 and v7 catch-up
- **WHEN** a developer opens `docs/app/documentation.md` after this refresh with context showing P7 and V0–V6.1 done
- **THEN** the header shows Through step covering P7 + V6.1 (or equivalent) and the snapshot no longer frames P7 edit HTTP or shipped v7 observability/harness/hybrid as future-only

#### Scenario: Maintenance log records the catch-up
- **WHEN** the refresh is finished
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for the new through-step with trigger noting P7 + post-P7/v7 catch-up

#### Scenario: Through-step does not overshoot context
- **WHEN** `docs/context.md` still lists a deferred v7 item (e.g. V6.2/V6.3) as not done
- **THEN** the manual does not claim those deferred modules as shipped

### Requirement: Module map and wiring include P7 and shipped v7 artifacts
The module map and imports/wiring pages MUST list as real (not stub) whatever `docs/context.md` marks implemented for P7 and post-P7/v7, including at minimum when ✅: trip day-edit HTTP + `rate_limit_trip_edit`, TripEditEvent UoW edit path, evaluation `mark_trip_edited` flag polish, `scripts/test_p7_smoke.py`, `LLMUsage` / `TravelState.token_usage`, Langfuse tracing facade + generate lifecycle, `src/evaluation/scorers.py` + `scripts/run_evals.py` + `evals/`, hybrid sparse/RRF / `places_v2` accessors, and fusion diagnostics when ✅. Stub callouts MUST remain only for packages still stubbed in context (evaluation HTTP; `auth/dependencies.py`; deferred embedding bump / cross-encoder if deferred).

#### Scenario: Junior looks up trip edit HTTP
- **WHEN** a developer opens the module map looking for trip day-edit routes after context marks P7 ✅
- **THEN** they see reorder/remove/add/reoptimize as real with ownership and rate-limit notes, not as “HTTP stubs”

#### Scenario: Junior looks up observability and evals
- **WHEN** a developer opens the module map looking for tracing or golden evals after context marks V2–V3 ✅
- **THEN** they see Langfuse/NoOp tracing, token usage persistence, and the golden harness runner as real, with empty keys = NoOp called out

#### Scenario: Evaluation HTTP remains stub
- **WHEN** a developer looks up evaluation HTTP while context still lists it as stub
- **THEN** the manual states evaluation HTTP is not implemented / not registered without inventing public APIs

### Requirement: How-to-change recipes cover P7 smoke, Langfuse keys, and golden evals
Recipes MUST mention running `python scripts/test_p7_smoke.py` (when context marks 7.6 ✅), setting optional `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` for live traces (empty = NoOp), and running `python scripts/run_evals.py --destination darjeeling` for golden regression (when V3 ✅). Recipes MUST NOT present evaluation HTTP as a live product API. Recipes MUST NOT tell juniors that golden pass_rate appears inside Langfuse unless that integration is explicitly built.

#### Scenario: Smoke and eval recipes after catch-up
- **WHEN** a developer follows verification recipes after this refresh
- **THEN** they are directed to P7 smoke, pytest, and the golden harness consistent with `docs/context.md`

#### Scenario: Langfuse optional path is documented
- **WHEN** a developer wants live token/trace visualization
- **THEN** the manual points them at existing `LANGFUSE_*` settings and states empty keys keep NoOp behavior

#### Scenario: No invented evaluation HTTP
- **WHEN** a developer reads how-to-change guidance after this refresh
- **THEN** they do not find evaluation list/detail HTTP presented as registered live routes

### Requirement: Architecture and notes docs light-touch after catch-up
`docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P7 / post-V6.1 `docs/context.md` (e.g. P7 edit still future-only, Langfuse generate wrap described as fully wired when it was not, token usage missing). Corrections MUST be minimal status/framing fixes. Stale planning notes in `docs/next_version.md` that claim `token_usage` is absent from `TravelState` MUST be corrected or clearly marked historical. `docs/context.md` MUST not overstate Langfuse wrapping if code has not yet landed the lifecycle calls (update after the wrap fix in the same change).

#### Scenario: context and notes match shipped observability
- **WHEN** a reader checks context / next_version notes after this change completes
- **THEN** they are not told that `token_usage` is missing from `TravelState`, and Langfuse generate lifecycle claims match the code

#### Scenario: system/lld status framing matches context
- **WHEN** a reader checks planner/trips/observability summaries after the catch-up
- **THEN** those rows do not contradict P7 ✅ and V2–V6.1 ✅ in context; evaluation HTTP may still be noted as stub
