# ADR-006 — Run tracking and idempotency scope

## Context

Blueprint v8.3 §21 asks for a record of run tracking and idempotency once generate can write `planner_runs`. Subslice 1.1 added the table only. Rows 1.2–1.4 attach a status machine, a client idempotency key, and `GET /api/v1/planner/runs/{run_id}`. The preference cache (parsed request, shared across sessions) already replays a plan and still saves a new trip. Those two keys answer different questions. Checkpoint, resume, leases, and workers stay deferred.

## Decision

The idempotency key is the `Idempotency-Key` header when it is 1–128 characters, otherwise a digest of the normalized plan request plus the session id. It is not the preference-cache key. `build_planner_cache_key` is unchanged. A new idempotency key may still use the cache and save a new trip. The same owner and key return the same run and the same trip.

This slice adds no checkpoint, no resume, no lease, and no worker. It adds no cancel route. Client disconnect still stops the in-flight generate task and, when tracking is on, moves a non-terminal run to `cancelled`.

`RUN_TRACKING_ENABLED` defaults to false. While it is false, generate does not write run rows and does not add `run_id` to SSE payloads.

## Alternatives

Use the preference-cache key as the idempotency key. Rejected. That key is shared across sessions, and a cache hit is required to save a new trip for a new submit.

Add `POST /api/v1/planner/runs/{run_id}/cancel`. Rejected. The in-flight task is local to the request. Cancelling it from a second request needs a lease or a worker, which this slice defers.

Store clarification text on the run. Rejected. No new column. The first stream still emits `clarification_needed`. A later read sees failure code `needs_clarification`.

## Consequences

Duplicate submits collapse only while the flag is on. Flag off keeps today's behavior, including a second trip for a second submit. GET stays available for rows that already exist so a client can poll after the flag is turned off. SSE event names do not change. `run_id` is an added field only when the flag is on.

## Migration and rollback

No migration. Deploy with the flag at its default, false. Rollback of generate behavior is `RUN_TRACKING_ENABLED=false`. Rollback of the route is removing the GET handler. Do not drop `planner_runs` for this rollback.

## Status

accepted
