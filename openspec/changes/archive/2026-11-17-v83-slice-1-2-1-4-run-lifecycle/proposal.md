## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §6.7, §9 rows **1.2**, **1.3**, and **1.4**, §13, and ADR-006 in §21) is the next Slice 1 work after the `planner_runs` table. There is no `docs/steps/step*.md` for these rows. Subslice 1.1 is implemented in the tree (model, flush-only repository, migration) and is not archived. Generate still does not write a run, a repeated submit still saves a second trip, and `GET /api/v1/planner/runs/{run_id}` is not a registered route. `docs/context.md` does not mention run tracking. The generate path, trip save, and SSE adapter are real modules, not stubs.

The user asked for rows 1.2, 1.3, and 1.4 in one change. The blueprint's "one PR per subslice" rule is overridden for this batch only. Each row's stop condition still applies inside the change.

## What Changes

- Add `RUN_TRACKING_ENABLED` on `Settings`, default `false`. Flag off keeps today's generate, save, and SSE payloads: no run rows and no `run_id` field. Flag on records one run per submit and drives it to a terminal status.
- Add a run lifecycle service that is the only writer of `PlannerRun.status`. Transitions are a fixed table. An LLM cannot set status. Illegal transitions fail.
- When the flag is on, resolve an idempotency key from the `Idempotency-Key` header, or from a hash of the normalized plan request plus the session. The same owner and key returns the same run and the same trip. `TripService.save_from_state` refuses a second insert when that run already has a `trip_id`, and it stores `trip_id` in the same commit as the trip.
- Add `GET /api/v1/planner/runs/{run_id}` as `ApiResponse`. Ownership matches trips: a guest cookie must equal the run's session; a mismatch is 403, not 404.
- When the flag is on, add `run_id` as an optional field on existing SSE payloads. Do not rename or remove SSE event names.
- Write ADR-006. The preference-cache key stays the parsed-request key. It is not the idempotency key.
- No **BREAKING** changes. Flag off is the current contract.

## Capabilities

### New Capabilities

- `planner-runs`: lifecycle, idempotency, and `GET /api/v1/planner/runs/{run_id}` on the table subslice 1.1 already added. This delta does not repeat the table requirements. Archive `v83-slice-1-1-planner-runs` before this change so the persistence requirements land first. This change retires that delta's rule that generate writes no run and that the GET route is absent: those remain true only while the flag is off.

### Modified Capabilities

- `planner-sse-generate`: flag off leaves the stream unchanged. Flag on may add `run_id` and may replay one existing terminal instead of starting a second generate. A repeated key does not save a second trip. A new key may still use the preference cache and save a new trip.
- `trips-repository-service`: `save_from_state` accepts an optional run id. When that run already points at a trip, it returns that trip. When it saves, it binds `trip_id` before commit. A call without a run id stays as it is today.
- `s0-architecture-guardrails`: G15 becomes an AST check that run status changes only in the run service. G15 leaves the deferred list.
- `s0-decision-records`: ADR-006 is an accepted record. ADR-001 through ADR-004 stay as they are.

## Impact

- **Work surface:** `src/planner/runs/**`, `src/planner/router.py`, `src/planner/schemas.py`, `src/trips/service.py`, `src/config.py`, `tests/planner/**`, `tests/trips/**`, `tests/architecture/**`, `docs/v8.2/adr/006-run-tracking-idempotency.md`, `docs/FE_guide.md`. `docs/context.md` is the last task only.
- **No new package.** No migration. No edit to `src/planner/cache.py` or `src/planner/service.py`.
- **APIs:** one new GET. `POST /api/v1/planner/generate` keeps its path, event names, and flag-off body. No cancel route.
- **Frontend repo:** untouched. `docs/FE_guide.md` documents the header, the GET, ownership, and the additive `run_id`.

## Non-goals

- No `POST /api/v1/planner/runs/{run_id}/cancel`. Disconnect already cancels the background task. A second request cannot see that task without a lease or a worker, and §9 defers both. ADR-006 records the deferral. Disconnect still moves a non-terminal run to `cancelled` when the flag is on.
- No checkpoint, resume, heartbeat, or new SSE event name.
- No change to `build_planner_cache_key`. A cache hit for a **new** idempotency key still saves a new trip.
- No edit to `PlannerService.generate`. Timeout, recursion, abort, and clarification are already on the returned state or the task exception. The router maps those to a terminal status. If a required outcome is not visible there, stop. Do not change SSE event names to surface it.
- No mid-run status for `resolving`, `researching`, or `validating` on the live generate path. Those values stay legal in the table for a later slice. This slice writes `accepted`, then `planning`, then one terminal status.
- No new failure-code column, no stored clarification question, and no exposure of `idempotency_key`, `input_hash`, or `session_id` on GET.
- No default-on flag. Soak stays off until a later rollout.
- No `docs/context.md` edit except the final task. The §19 completion report goes in the PR description.
- No frontend app change.

## Constraints

From `AGENT.md` and the v8.3 invariants:

- Router → Service → Repository. The router calls the run service and `TripService`. It does not import a repository.
- `PlannerService` stays free of `Request`, `StreamingResponse`, and `request.is_disconnected`.
- LLM, geo, and `travel_engine` stay untouched. The run service does not call the network.
- Settings only through `get_settings()`. No new package.
- GET returns `ApiResponse[T]`. SSE stays an event stream, not an `ApiResponse`.
- Existing `/api/v1` paths and SSE event names stay. New fields are additive and appear only when the flag is on.

Blueprint path notes, confirmed against the checkout:

- Row 1.2 names `src/planner/service.py`. This change does not edit it, for the stop condition "planner service contract would change SSE".
- The flag lives in `src/config.py`. Row 1.1 left that file alone because nothing read a flag. Rows 1.2 and 1.3 roll back by turning the flag off, and G11 already expects `RUN_TRACKING_ENABLED` to default false once the field exists. `.env.example` does not list planner settings; do not add a new dotenv file.
- G15's AST test and `tests/architecture/VIOLATIONS.md` sit outside the row path cells. §10 requires that test once the run service exists. Subslice 0.5 deferred it until then.
- ADR-006 sits under `docs/v8.2/adr/`, next to ADR-001–004. Row 1.3 says to write that record instead of merging the idempotency key with the preference cache.
- `docs/FE_guide.md` is in row 1.4's allowed paths. `docs/context.md` is the OpenSpec end-of-step update, not a behavior change.
