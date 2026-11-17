## 1. Confirm scope

- [ ] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.7, §9 rows 1.2–1.4, §13, and this change's `proposal.md`, `design.md`, and delta specs. There is no `docs/steps/step*.md` for these rows.
- [ ] 1.2 Confirm `PlannerRun`, `PlannerRunRepository`, and the `planner_runs` migration from subslice 1.1 are in the tree. Do not add a migration. Do not edit `src/planner/service.py`, `src/planner/cache.py` (except calling `normalize_raw_input`), `build_planner_cache_key`, or the frontend repo.

## 2. Flag and decision record

- [ ] 2.1 Add `RUN_TRACKING_ENABLED: bool = False` on `Settings` in `src/config.py`. Do not edit `.env.example`.
- [ ] 2.2 Add `docs/v8.2/adr/006-run-tracking-idempotency.md` with the ADR-002 sections and status `accepted`. State that the idempotency key is not the preference-cache key, the cache key is unchanged, there is no cancel route, checkpoint, resume, lease, or worker, disconnect still stops an in-flight generate, and the flag defaults to false.

## 3. Pure helpers

- [ ] 3.1 Add idempotency helpers under `src/planner/runs/` that use `normalize_raw_input`. Header length 1..128 wins. Otherwise `input_hash` is sha256 of `destination:raw_hash:days:rounded lat:rounded lng`, and the fallback key is sha256 of that material plus the session id. Accommodation label is excluded. Unit-test same body same session, two sessions, over-long header, and that the result is not `build_planner_cache_key`.
- [ ] 3.2 Add the pure outcome mapper from design Decision 3. Unit-test timeout, recursion, `WandrLLMError`, clarification, missing terminal, clean save, geo or routing fallback, abort with no trip, and disconnect.

## 4. Lifecycle service

- [ ] 4.1 Add `PlannerRunService` in `src/planner/runs/service.py`. `transition` enforces the legal table in the planner-runs spec, flushes, and does not commit. An illegal target, including any leave from a terminal status, raises and leaves the row unchanged. `start` inserts `accepted` with `workflow_version="planner-v6.1"`, `model_name` from `LLM_MODEL`, provider before the first `/`, null `fallback_reason`, and the given `input_hash`, commits, then moves to `planning` and commits.
- [ ] 4.2 On `IntegrityError`, roll back and re-read the winning row. An authenticated reuse of a guest row with the same session and key sets `user_id`; a partial-unique conflict rolls back and re-reads by user key. Never return another user's run.
- [ ] 4.3 Add service tests for one legal edge that generate does not use (`validating` → `partial`), one illegal edge (`completed` → `planning`), and a `start` row that is `planning` with the model fields set.

## 5. Guardrail

- [ ] 5.1 Add an AST test that fails when a file other than `src/planner/runs/service.py` assigns `.status` and references `PlannerRun` or `RunStatus`. Remove G15 from the deferred section of `tests/architecture/VIOLATIONS.md`. Update `test_deferred_rules_documented` so G8, G9, G10, G12, G13, and G14 stay listed and G15 does not. Do not edit `src/core/observability/tracing.py`.

## 6. Save guard

- [ ] 6.1 Extend `TripService.save_from_state` with optional `run_id`. No run id: do not read or write a run. Run already has `trip_id`: lock the row, return that trip, do not insert. New trip: set `trip_id` and call `transition` to `completed` or `degraded` from the state fallback flags in the same transaction, before the existing commit. Unusable schedule: return `None` and do not set `trip_id`. `TripService` must not import `PlannerService`. `PlannerRunService` must not import `TripService`.
- [ ] 6.2 Add tests, marked so `-k idempotent` selects them: save without a run id inserts no run; second save for a run returns the first trip; after a successful save the run's `trip_id` is set before the method returns.

## 7. Generate wiring

- [ ] 7.1 In `src/planner/router.py`, when the flag is off, keep today's cache and generate path: ignore `Idempotency-Key`, write no run, add no `run_id`. When the flag is on, resolve the key, apply design Decision 4 before cache lookup, and commit the new run to `planning` before `create_task`. Copy ids and coordinates into locals before that commit. Do not pass the request session into the background task.
- [ ] 7.2 After the task, map the outcome and either save with `run_id` or `transition` and commit. Disconnect of a non-terminal run becomes `cancelled` / `client_disconnect`. Add `run_id` on every yielded SSE data object only when the flag is on. Do not add or rename an event. If an outcome in the planner-runs table is not visible from the task result, the task exception, or disconnect, stop.
- [ ] 7.3 Add planner tests, selected by `-k idempotent`, with the flag on: double submit creates one trip; an in-progress duplicate returns one `error` `run_in_progress` and does not start generate; a repeated key with a different body reuses the run; a new key on a cache hit still saves a new trip; flag off emits no `run_id` and writes no run.

## 8. GET run

- [ ] 8.1 Add `RunNotFoundError` (404) and `RunForbiddenError` (403) beside the run service, and `PlannerRunOut` in `src/planner/schemas.py` with `run_id`, `status`, `failure_code`, `trip_id`, `created_at`, `updated_at`. Register `GET /api/v1/planner/runs/{run_id}` as `ApiResponse`. Unknown id is 404. Ownership matches trips: mismatch is 403, not 404. The body omits the idempotency key, input hash, and session id. The router calls the service, not the repository. Do not add a rate limiter.
- [ ] 8.2 Test owner 200, wrong session 403, unknown id 404, and that the 1.1 unknown-id test still sees 404. Test that a committed `trip_id` is returned even when no SSE frame was built.
- [ ] 8.3 Document the header, the GET, ownership, additive `run_id` when the server flag is on, `run_in_progress`, and the absence of a cancel route in `docs/FE_guide.md`.

## 9. Context and verify

- [ ] 9.1 Update `docs/context.md`: bump Last updated, and record that Slice 1 run tracking is implemented behind `RUN_TRACKING_ENABLED` (default false) with GET `/api/v1/planner/runs/{run_id}`. Keep the existing DNS next-step sentence. Add that the next blueprint slice is Slice 2. Do not edit the blueprint.
- [ ] 9.2 Run `pytest tests/planner/runs -v`, `pytest tests/trips tests/planner -k idempotent`, and `pytest tests/snapshots tests/planner tests/architecture -q`. All must exit 0. A snapshot diff that is only `run_id` or a new event name means the flag-off path is wrong; fix that before anything else.
- [ ] 9.3 Confirm the diff has no new package, no migration, no cancel route, and no edit to `src/planner/service.py`. Put the blueprint §19 completion report in the PR description. Do not archive this change before `v83-slice-1-1-planner-runs`.
