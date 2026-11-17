## Context

See proposal.md for why rows 1.2–1.4 land together. Specs: `specs/planner-runs/spec.md`, `specs/planner-sse-generate/spec.md`, `specs/trips-repository-service/spec.md`, `specs/s0-architecture-guardrails/spec.md`, `specs/s0-decision-records/spec.md`.

Subslice 1.1 already added `PlannerRun`, `RunStatus`, and a flush-only `PlannerRunRepository` (`get_by_session_key`, `get_by_user_key`). There is no lifecycle service. `POST /api/v1/planner/generate` streams SSE from `src/planner/router.py`. `PlannerService.generate` catches timeout and recursion, returns a state, and does not take a database session. The router saves only after the background task finishes, on the request's `AsyncSession`. That session must stay idle while the task runs. `save_from_state` commits inside the method. The preference-cache key is `build_planner_cache_key` in `src/planner/cache.py` (destination, normalized raw input, days, rounded base). A cache hit still creates a new trip. G15 is still deferred in `tests/architecture/VIOLATIONS.md`. `RUN_TRACKING_ENABLED` is not on `Settings` yet; the architecture helper already expects it to default false once the field exists.

This change performs no external I/O. The generate timeout, provider calls, and cache backend stay as they are. No new timeout, retry, or fallback client.

## Goals / Non-Goals

**Goals:**

- One lifecycle service owns every status write, including the trip bind inside `save_from_state`.
- Flag off is the current generate path. Flag on commits a run before work starts, ends it terminal, and returns the same trip for the same owner and key.
- GET follows the trip ownership rule and the existing error envelope.

**Non-Goals:**

- See proposal.md. In particular: no edit to `src/planner/service.py` or `src/planner/cache.py`, no cancel route, no migration.

## Decisions

### 1. Flag gates writes, not the GET

Add `RUN_TRACKING_ENABLED: bool = False` on `Settings`. Tests that need tracking override settings in the test. Do not add a dotenv file. `.env.example` has no planner block; leave it.

Flag off: the router skips key resolution, run insert, and `run_id`. `save_from_state` without a run id does not touch `planner_runs`. Flag on: the router does the flow below. GET reads an existing row either way, so a client that already received a `run_id` can still poll after the flag is turned off.

Alternative considered: GET returns 404 while the flag is off. Rejected. The 1.4 rollback is removing the route. The 1.2 rollback is "no new run rows." Hiding old rows is a second switch the blueprint does not ask for.

### 2. Lifecycle service is the only status writer

`PlannerRunService` in `src/planner/runs/service.py` is the only module that assigns `PlannerRun.status`. The repository stays flush-only. The router and `TripService` call the service. They do not import the repository. G5 stays intact.

`transition(run, new_status, failure_code)` checks the legal table in the planner-runs spec, assigns status, sets or clears `failure_code`, and flushes. It does not commit. An illegal target raises a domain error and does not write. Terminal statuses have no outbound edge.

`start(...)` inserts `accepted`, fills `input_hash`, `workflow_version`, `model_name`, and `provider`, commits, then `transition` to `planning` and commits again. Both commits happen before `create_task`. The request session is then idle until the task finishes. Locals already hold `session_id`, `user_id`, destination id, and base coordinates, so the commit may expire the destination ORM object without another read.

Constants, not new settings: `workflow_version="planner-v6.1"`. `model_name` is `settings.LLM_MODEL`. `provider` is the substring before the first `/`, or the whole string when there is no slash. `fallback_reason` stays null. There is no second model to record.

Alternative considered: update status from `PlannerService` during `on_event`. Rejected. The emit callback is synchronous, the service has no session, and a mid-graph write would use the session while the generator might also touch it. The live path only needs `accepted` → `planning` → one terminal status.

### 3. The router maps an outcome the service already returns

Do not change `PlannerService.generate`. A pure function in `src/planner/runs/outcomes.py` (no I/O) maps what the router can already see:

| What the router sees | Status | Failure code |
|---|---|---|
| Task cancelled, or disconnect before a terminal status | `cancelled` | `client_disconnect` |
| Returned state or terminal `error` code `generation_timeout` | `timed_out` | `generation_timeout` |
| Code `graph_recursion_limit` | `failed` | `graph_recursion_limit` |
| Task raises `WandrLLMError` | `failed` | `llm_unavailable` |
| `needs_clarification` on the returned state | `failed` | `needs_clarification` |
| No terminal event | `failed` | `missing_terminal` |
| `itinerary_done` and a saved trip, `used_geo_fallback` or `used_osrm_fallback` | `degraded` | empty |
| `itinerary_done` and a saved trip, neither fallback | `completed` | empty |
| Any other failed task or abort with no trip | `failed` | `generation_aborted` |

The first client's SSE event is still chosen by the existing emitter. Clarification stays `clarification_needed` on that first response. The failure code is only the run row and, for a later replay, the `error` code.

`degraded` versus `completed` is decided inside `save_from_state` from the state flags, so the signature stays `(state, user_id, session_id, run_id=None)`. The lifecycle service performs the transition in that same transaction, before the existing commit.

If a required outcome is not on the returned state, the task exception, or the disconnect path, stop. Do not add an SSE event name to expose it.

### 4. Idempotency key is not the cache key

Header `Idempotency-Key`. Strip it. Length 1..128: store it as the key. Missing, blank, or longer: fall back. Do not answer 400. Generate must still run.

Fallback and `input_hash` use `normalize_raw_input` from `src/planner/cache.py` so whitespace rules cannot drift. They do not call `build_planner_cache_key`.

```
raw_hash = sha256(normalized raw input)
body     = "{destination_id}:{raw_hash}:{days_or_0}:{round(lat,3)}:{round(lng,3)}"
input_hash   = sha256(body)                         # 64 hex, no session
fallback key = sha256(body + ":" + session_id)      # 64 hex
```

`days_or_0` is `body.days` or `0`. Accommodation label is not included.

Lookup, flag on, before cache and before generate:

1. Authenticated: `get_by_user_key`. If that misses, `get_by_session_key` only when `user_id` is null or equals the caller. A different user's row is not a hit.
2. Guest: `get_by_session_key` only.
3. Miss: `start`. On `IntegrityError`, roll the session back, re-read, and treat it as a hit. Do not start a second graph.
4. Hit, not terminal: one SSE `error` / `run_in_progress` with `run_id`. No cache, no generate, no save.
5. Hit, terminal, with `trip_id`: one `itinerary_done` with that `trip_id` and `run_id`. No save.
6. Hit, terminal, no trip: one `error` whose code is the stored failure code, plus `run_id`.
7. Miss that this request won: existing cache-or-generate path. A new key may still cache-hit and save a new trip.

When an authenticated caller reuses a guest row (`user_id` null, same session and key), set `user_id` on that row before reuse. If that update hits the partial unique index, roll back and re-read by user key. Same user and same key stay one run.

A repeated key with a different body returns the original run. Do not compare `input_hash` to reject the call. Do not update `input_hash`.

Alternative considered: 409 when the body hash differs. Rejected. The blueprint says the same key returns the same run, not a conflict.

Alternative considered: using the cache key as the idempotency key. Rejected. The cache is shared across sessions and a hit is required to save a new trip for a new key. ADR-006 records that split.

### 5. One commit binds the trip

`save_from_state(..., run_id=None)`:

- No run id: today's insert and commit. No run read.
- Run id set and `trip_id` already set: load that trip and return it. No insert. Lock the run row (`SELECT ... FOR UPDATE`) so two saves cannot both pass the empty check.
- Run id set, no trip yet, schedule usable: insert the trip as today, call `transition` to `completed` or `degraded`, set `trip_id`, then the existing commit.
- Unusable schedule: return `None` and do not set `trip_id`. The router then transitions to the non-save outcome and commits.

After that commit, GET can see `trip_id` even if the process dies before `yield`.

`TripService` may import `PlannerRunService`. It must not import `PlannerService`. `PlannerRunService` must not import `TripService`.

### 6. GET is a thin route

`GET /api/v1/planner/runs/{run_id}` on the planner router. `optional_auth`. Session cookie `wandr_session`, same helper the generate path uses. `PlannerRunOut` in `src/planner/schemas.py` with `run_id`, `status`, `failure_code`, `trip_id`, `created_at`, `updated_at`. Response is `ApiResponse[PlannerRunOut]`.

`RunNotFoundError` subclasses `NotFoundError` (404, `not_found`). `RunForbiddenError` subclasses `ForbiddenError` (403, `forbidden`). Missing row first, then the same predicate as `TripService.assert_can_access`: guest cookie must equal `session_id`; authenticated caller matches `user_id`, or matches the session when `user_id` is null.

Do not add a rate limiter. `RATE_LIMIT_PLANNER_PATH` is the generate path only.

When the flag is on, a small wrapper adds `run_id` onto each yielded SSE data dict, including replay frames. Event names stay. Flag off skips the wrapper.

### 7. G15 and the deferred list

An AST test fails when a file other than `src/planner/runs/service.py` assigns `.status` and that file references `PlannerRun` or `RunStatus`. `models.py` is exempt only for the column declaration, not for an instance assignment. Update `test_deferred_rules_documented` so G8, G9, G10, G12, G13, and G14 stay documented and G15 does not. Remove the G15 row from the deferred section of `VIOLATIONS.md`. Do not edit `src/core/observability/tracing.py`.

### 8. ADR-006

`docs/v8.2/adr/006-run-tracking-idempotency.md`, same sections as ADR-002. Status `accepted`. It records decisions 1, 4, and the refusal of cancel, checkpoint, resume, lease, and worker.

## Risks / Trade-offs

- [Early commit expires ORM objects loaded in the request] → Copy ids and coordinates into locals before `start`. Do not touch `dest` after that commit.
- [IntegrityError leaves the session unusable] → Roll back before the re-read. Do not continue the failed insert.
- [Same session used inside the background task] → The task must not receive the request session. Run writes happen before the task and after it, on the generator side.
- [Flag-on replay of a clarification is `error` / `needs_clarification`, not the original question] → The question is not stored. The first client still gets `clarification_needed`. A duplicate polls GET for the code. No new column.
- [Live path never writes `partial`, `resolving`, `researching`, or `validating`] → The table still allows those edges for a direct service call. Generate does not fake them.
- [`completed` → anything is illegal, so a bug that saves twice must hit the trip-id guard, not a second transition] → The guard returns the existing trip before `transition`.
- [G15 AST misses a status write that does not assign `.status`] → Review `update(... status ...)` in the diff. The repository must not grow a status method.
- [1.1's "route is absent" requirement contradicts this GET] → Archive that change first. This delta removes that requirement.

## Migration Plan

1. No Alembic revision. Deploy the code with the default flag false. Generate matches today. GET of an unknown id is 404.
2. Rollback of generate behavior is `RUN_TRACKING_ENABLED=false`. Rows already written remain readable by their owners.
3. Rollback of the route is deleting the GET handler. Do not drop `planner_runs`.
4. Verify, in order: `pytest tests/planner/runs -v`, `pytest tests/trips tests/planner -k idempotent`, `pytest tests/snapshots tests/planner tests/architecture -q`. Snapshot failures that are only `run_id` or a new event name mean the flag-off path is wrong. Stop and fix that before any other change.

## Open Questions

None. Key format, lookup order, cancel, and the cache split are decided above.
