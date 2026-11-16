## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **0.4**, and §21) asks for ADR-001 through ADR-004 and for every `[SET IN S0]` cell in §4 to be filled from the Slice 0 baseline. There is no `docs/steps/step*.md` for this work. The decisions are still only an index. The four relative targets (p50, LLM calls, tokens, cost) have no measured baseline, and p95 has not been measured against the 45s ceiling.

## What Changes

- Add four decision records under `docs/v8.2/adr/`: modular monolith (001), `/api/v1` additive compatibility (002), bounded execution (003), and deterministic validator versus LLM judge (004). Each record has context, decision, alternatives, consequences, migration and rollback, and status.
- Add `docs/v8.2/s0_targets.md` that restates the §4 table. The four `[SET IN S0]` cells stay placeholders. p95 stays "not measured", so the row 0.4 stop ("halt if p95 is already over 45s") is recorded as not evaluable.
- Cite `docs/v8.2/baseline_metrics.md` from subslice 0.3 as the only source for a number. A metric that doc marks unmeasured is not given a value in this change.

No production behavior changes. No **BREAKING** changes. The blueprint file is not edited, so its §4 placeholders remain. That is intentional: row 0.4 may write only `docs/v8.2/**`, and filling a placeholder without a measurement would invent the release gate.

## Capabilities

### New Capabilities

- `s0-decision-records`: ADR-001–ADR-004 exist as accepted decisions, and the Slice 0 targets record keeps every unmeasured `[SET IN S0]` cell as a placeholder with a halt note.

### Modified Capabilities

(none — this change does not alter `eval-golden-harness`, `legacy-api-snapshots`, or the 0.3 baseline-record requirements. It reads the baseline doc. It does not change planner, HTTP, or judge behavior. `planner/runs/`, `location_intelligence/`, and the judge are still absent; these ADRs do not create them.)

## Impact

- **Work surface:** guideagent docs under `docs/v8.2/**` only.
- **Files written:** `docs/v8.2/adr/001-modular-monolith.md`, `docs/v8.2/adr/002-api-v1-compat.md`, `docs/v8.2/adr/003-bounded-execution.md`, `docs/v8.2/adr/004-deterministic-vs-judge.md`, and `docs/v8.2/s0_targets.md`.
- **Depends on:** subslice 0.3 applied, so `docs/v8.2/baseline_metrics.md` exists. If 0.3 stopped because the two eval runs disagreed, this change does not start.
- **No impact on:** application code, tests, migrations, settings, dependencies, HTTP paths, DTO shapes, SSE event names, the eval runner, Docker, `docs/context.md`, or `docs/steps/wandr_blueprint_version8.md`.
- **Downstream:** Slice 3 still may not start while `[SET IN S0]` is unset. Subslice 0.5 does not need these numbers and stays a separate change. Slice 1 waits for 0.5 as well.

## Non-goals

- No numeric fill-in of p50, LLM calls per trip, tokens per trip, or cost per trip.
- No claim that generate p95 is under or over 45 seconds.
- No edit to §4 inside `docs/steps/wandr_blueprint_version8.md`. The verify line "targets table has no placeholders" cannot be met inside this row's allowed paths without a measurement. This change records that halt. It does not redefine the verify line.
- No ADR-005 through ADR-016. Those wait for their own slices.
- No architecture tests (0.5), no runner changes, no product decision to raise `PLANNER_GENERATION_TIMEOUT_SECONDS`.
- No update to `docs/context.md`.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay inside `docs/v8.2/**`. Touching the blueprint, `src/`, `scripts/`, or tests is a stop.
- Copy decisions that §21 and the invariants already state. An ADR does not add a flag, endpoint, or module.
- Leave a `[SET IN S0]` cell as a placeholder when `baseline_metrics.md` says that metric is unmeasured. Inventing a multiplier base is a stop.
- Not update `docs/context.md`. Row 0.4's allowed paths forbid the context update the OpenSpec repo rule would otherwise ask for. The targets file is the record.
- Treat "p95 already > 45s" as not evaluable until a later change, whose allowed paths include measurement, reports a p95. This subslice does not approve a longer SSE ceiling.

Row 0.4's verify ("no placeholders") conflicts with its allowed paths and with the missing measurements. The conflict rule in blueprint §2 applies: this subslice writes the halt in `docs/v8.2/s0_targets.md` and does not pick a number in order to look finished.
