# ADR-004 — Deterministic validator versus LLM judge

## Context

Blueprint v8.3 §21 assigns deterministic-validator and LLM-judge responsibilities to invariants N3 and N9. N3 says a deterministic critical finding is never overridden by a judge, a score, or an agent. N9 says an uncalibrated judge never gates a request and never triggers a repair on the request path. The repository audit found no judge package. Slice 7 is the only slice that may add a judge, and only behind a flag, after the earlier slices ship. §16 also defers in-path judge repairs.

## Decision

Deterministic critical findings are never overridden by a judge, a score, or an agent (N3). An uncalibrated judge never gates or repairs the request path (N9).

## Alternatives

Let a model score replace a failing validator and repair the itinerary before the response is sent. Rejected. N3 and N9 already forbid that, and §16 defers in-path repairs.

## Consequences

This record does not add a judge, a prompt, or a flag. `src/planner/reasoning/` and `src/evaluation/judge/` stay absent. Slice 7 may add an advisory critic later. That critic still cannot override a critical finding or repair the request. Slice 2 may add an offline judge scaffold. That scaffold stays off the request path.

## Migration and rollback

No migration and no deploy. Rollback is deleting this file. Request-path validation stays the existing deterministic validator.

## Status

accepted
