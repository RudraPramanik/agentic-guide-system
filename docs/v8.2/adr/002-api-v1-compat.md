# ADR-002 — `/api/v1` additive compatibility

## Context

Blueprint v8.3 §21 names `/api/v1` backward compatibility with additive evolution. The inherited invariant is that existing HTTP paths, DTO shapes, and SSE event names stay compatible unless a later ADR approves a break. Envelopes stay `ApiResponse[T]` and `PaginatedResponse[T]`. Subslice 0.2 froze the current contract in snapshot fixtures. This record does not add a path.

## Decision

Existing `/api/v1` paths, DTO shapes, and SSE event names stay compatible. Evolution is additive. `ApiResponse` and `PaginatedResponse` remain the envelopes. A breaking change needs its own ADR.

## Alternatives

Version the planner under `/api/v2` for location and run-status fields. Rejected. The blueprint keeps one v1 contract and allows additive fields on the existing paths.

## Consequences

This record does not add an endpoint, a DTO field, or an SSE event name. Slice 1 may add `GET /api/v1/planner/runs/{run_id}` only as an additive route, and only in that slice. The snapshot suite remains the check that legacy responses stay put. `docs/FE_guide.md` is unchanged here.

## Migration and rollback

No migration and no deploy. Rollback is deleting this file. Clients keep calling the paths they call today.

## Status

accepted
