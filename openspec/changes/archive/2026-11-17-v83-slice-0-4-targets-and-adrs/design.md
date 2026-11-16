## Context

See proposal.md — Why. Blueprint §21 names ADR-001–ADR-004 in one line each and says every ADR has context, decision, alternatives, consequences, migration and rollback, and status. §4 still contains `[SET IN S0]` on p50, LLM calls, tokens, and cost. The p95 row is already "≤ 45 s" and is not a placeholder. Subslice 0.4 may write only `docs/v8.2/**`, so the §4 table in `docs/steps/wandr_blueprint_version8.md` cannot be edited here. This change starts only after `docs/v8.2/baseline_metrics.md` exists. It adds no I/O, so there is no new timeout, retry, or fallback. `travel_engine/` is not edited. The judge and `planner/runs/` are absent.

## Goals / Non-Goals

**Goals:**

- Four accepted records whose decisions match the blueprint invariants already in force.
- A targets file a later slice can cite without opening the blueprint, including an explicit halt where a number is missing.

**Non-Goals:**

- Re-litigating the four decisions.
- Editing §4 in the blueprint so its verify line looks green.

## Decisions

### 1. Status is accepted

Each ADR status is `accepted`. The decision text is the blueprint's existing rule, not a new product choice.

| ADR | Decision text the file must record |
|---|---|
| 001 | v8.3 stays one process. New work lands in the existing package layout. Microservices stay deferred. |
| 002 | Existing `/api/v1` paths, DTO shapes, and SSE event names stay compatible. Evolution is additive. `ApiResponse` / `PaginatedResponse` remain the envelopes. A breaking change needs its own ADR. |
| 003 | Generate p95 stays ≤ 45 s (`PLANNER_GENERATION_TIMEOUT_SECONDS`). The ceiling is not raised to fit a feature. Work that cannot fit becomes a background job with progress and run status, decided later with a measurement, not in this file. |
| 004 | Deterministic critical findings are never overridden by a judge, a score, or an agent (N3). An uncalibrated judge never gates or repairs the request path (N9). |

Alternative considered: status `proposed` until a human signs. Rejected. Row 0.4's job is to record decisions §21 already lists. Leaving them proposed would not unblock any later slice and would hide the lock.

### 2. Targets live beside the blueprint, not inside it

`docs/v8.2/s0_targets.md` copies the §4 rows and adds a source column: `baseline_metrics.md` for the fixtures-only pass rate, `unmeasured` for the four placeholders and for p95. The halt paragraph states that the blueprint verify line "targets table has no placeholders" is unmet, that the blueprint file was left unchanged because it is outside `docs/v8.2/**`, and that Slice 3 does not start on those gates.

Alternative considered: edit §4 in place and delete the placeholder tokens. Rejected. That file is outside the allowed paths, and the numbers do not exist.

### 3. Apply order

Read `baseline_metrics.md` before writing `s0_targets.md`. If heading "Halt" in that doc says the fixtures-only pair disagreed, stop this change and do not write the ADR files. A missing metrics doc is the same stop.

## Risks / Trade-offs

- [A reader of the blueprint still sees `[SET IN S0]` and may think 0.4 was skipped] → The targets doc is the citation later slices use, and it points at the blueprint line it is not allowed to edit.
- [Accepted ADRs get treated as permission to build Slice 1 or the judge] → Each ADR's consequences say the module is still absent and name the later slice that may add it.
- [Someone multiplies the fixtures-only pass rate into a latency target] → The targets doc may quote the pass rate only as a pass rate. The four relative gates stay placeholders.

## Migration Plan

Write the four ADR files, then `s0_targets.md`. No migration and no deploy.

Rollback: delete `docs/v8.2/adr/001-modular-monolith.md`, `002-api-v1-compat.md`, `003-bounded-execution.md`, `004-deterministic-vs-judge.md`, and `docs/v8.2/s0_targets.md`.
