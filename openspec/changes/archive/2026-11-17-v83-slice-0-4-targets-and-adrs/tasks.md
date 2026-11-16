## 1. Preflight

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §4, §9 row 0.4, and §21, plus this change's `proposal.md`, `design.md`, and `specs/s0-decision-records/spec.md`.
- [x] 1.2 Confirm `docs/v8.2/baseline_metrics.md` exists. If it is missing, or its Halt heading says the fixtures-only pair disagreed, stop this change and do not write ADR files.

## 2. Decision records

- [x] 2.1 Write `docs/v8.2/adr/001-modular-monolith.md` with context, decision, alternatives, consequences, migration and rollback, and status `accepted`. Decision: one process, existing package layout, microservices deferred. Consequences: this record does not create a new service.
- [x] 2.2 Write `docs/v8.2/adr/002-api-v1-compat.md` the same way. Decision: existing `/api/v1` paths, DTO shapes, and SSE event names stay compatible; evolution is additive; a break needs its own ADR.
- [x] 2.3 Write `docs/v8.2/adr/003-bounded-execution.md` the same way. Decision: generate p95 stays ≤ 45 s and the ceiling is not raised in this record. Work that cannot fit waits for a later measured decision.
- [x] 2.4 Write `docs/v8.2/adr/004-deterministic-vs-judge.md` the same way. Decision: deterministic critical findings are never overridden (N3); an uncalibrated judge never gates or repairs the request path (N9). The judge module stays absent.

## 3. Targets record

- [x] 3.1 Write `docs/v8.2/s0_targets.md` restating the §4 table. Quote the fixtures-only pass rate only as a pass rate. Leave p50, LLM calls, tokens, and cost as `[SET IN S0]` when the metrics doc marks them unmeasured.
- [x] 3.2 Record p95 as not measured, record the "already over 45 s" stop as not evaluable, and state that Slice 3 does not start on the four relative gates until a measured baseline exists. Do not edit `docs/steps/wandr_blueprint_version8.md`.

## 4. Verify

- [x] 4.1 Confirm the diff is only the four ADR files and `docs/v8.2/s0_targets.md`. No `src/` edit, no `scripts/` edit, no blueprint edit, no `docs/context.md` edit. Row 0.4's allowed paths forbid the context update the OpenSpec repo rule would otherwise ask for. Put the blueprint §19 completion report in the PR description, not in a new file.
- [x] 4.2 Confirm no `[SET IN S0]` cell in `s0_targets.md` was replaced with a number, and that none of the ADR files add a module, flag, or endpoint.
