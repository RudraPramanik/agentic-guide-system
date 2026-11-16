# ADR-003 — Bounded execution

## Context

Blueprint v8.3 §21 names bounded execution and loop prevention for the planner and any later reasoning budgets. §4 sets generate p95 at ≤ 45 seconds, the existing `PLANNER_GENERATION_TIMEOUT_SECONDS` default in `src/config.py`. That ceiling is never raised to make a feature fit. A feature that cannot finish inside it becomes a background job with progress and run status, decided with a measurement. `docs/v8.2/baseline_metrics.md` marks p95 unmeasured, so this record does not say the live generate is under or over 45 seconds. `planner/runs/` is absent.

## Decision

Generate p95 stays ≤ 45 seconds (`PLANNER_GENERATION_TIMEOUT_SECONDS`). The ceiling is not raised to fit a feature. Work that cannot fit becomes a background job with progress and run status, decided later with a measurement, not in this file.

## Alternatives

Raise the SSE timeout so a slower planner still finishes in the request. Rejected. §4 forbids raising the ceiling to make a feature fit.

## Consequences

This record does not change `PLANNER_GENERATION_TIMEOUT_SECONDS` and does not add run tracking. Slice 1 is the slice that may add run status. Slice 7 budgets, if that slice is ever built, stay inside this ceiling. The row 0.4 stop "halt if p95 is already over 45 seconds" is not evaluable until a later change measures p95. See `docs/v8.2/s0_targets.md`.

## Migration and rollback

No migration and no deploy. Rollback is deleting this file. The timeout setting stays at its current default.

## Status

accepted
