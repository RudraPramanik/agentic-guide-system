## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **0.3**) is the next Slice 0 step after the archived 0.1 audit and 0.2 snapshots. There is no `docs/steps/step*.md` for this work. Later slices need a frozen, repeatable baseline before any planner behavior change, and the file at `evals/baselines/darjeeling.json` is an older live generate (sha `3b58df2`, pass rate 0.67). It is not that baseline.

## What Changes

- Run the existing `scripts/run_evals.py` twice with `--destination darjeeling --fixtures-only`. Compare pass rate, case id, passed, reasons, and mode. Ignore timestamp and run filename.
- When those two runs match, freeze that report as `evals/baselines/darjeeling.json` with the runner's existing `--update-baseline` flag.
- Add `docs/v8.2/baseline_metrics.md` with the measured pass rate and an explicit unmeasured list for every other metric named in row 0.3.
- Record the retired live report (sha, timestamp, pass rate) in that doc. Leave files under `evals/runs/` in place.

No production behavior changes. No **BREAKING** changes. The regression file the runner already reads is replaced only after the two fixtures-only runs match.

## Capabilities

### New Capabilities

- `s0-baseline-record`: the Slice 0 baseline is a fixtures-only Darjeeling report that two runs agree on, plus a metrics doc that keeps unmeasured metrics labeled unmeasured.

### Modified Capabilities

(none — `openspec/specs/eval-golden-harness/spec.md` already describes the runner, scorers, and `--update-baseline`. This change does not alter those requirements. `scripts/run_evals.py` and `src/evaluation/scorers.py` stay as they are. The golden harness is real code; evaluation HTTP in `docs/context.md` is still a stub and is not used here.)

## Impact

- **Work surface:** guideagent docs and the Darjeeling baseline file. `scripts/run_evals.py` is invoked and not edited.
- **Files written:** `docs/v8.2/baseline_metrics.md` and, only after two matching runs, `evals/baselines/darjeeling.json`. Each run also writes a new file under `evals/runs/`, which the existing runner already does.
- **No impact on:** application code, tests, migrations, settings, dependencies, HTTP paths, DTO shapes, SSE event names, Docker, or `docs/context.md`.
- **Downstream:** subslice 0.4 reads the metrics doc and must not invent numbers the doc marks unmeasured. Slice 1 still waits for 0.4 and 0.5.

## Non-goals

- No edits to `scripts/`, `src/`, `tests/`, `evals/golden/`, `evals/fixtures/`, or `evals/runs/`.
- No live `PlannerService.generate`, no LLM key, no Qdrant, no OSRM.
- No new metrics code for invalid-trip rate, duplicate rate, coherence, schedule feasibility, p50, p95, LLM calls, tokens, cost, fallback rate, or persistence failures. Row 0.3's allowed paths forbid that work.
- No `[SET IN S0]` fill-in and no ADR-001–ADR-004 (those are 0.4).
- No architecture tests (0.5).
- No edits to `docs/steps/wandr_blueprint_version8.md` or `docs/context.md`.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay inside `docs/v8.2/**` and `evals/baselines/**`, plus read-only use of `scripts/run_evals.py`. Any other write is a stop.
- Treat a mismatch between the two fixtures-only runs as the row 0.3 stop: do not write `--update-baseline`, do not edit the runner to force a match, and report the disagreeing case ids.
- Not treat the August live baseline as the v8.3 measurement. Fixtures under `evals/fixtures/` have no latency, token, cost, or schedule fields. Those metrics stay unmeasured.
- Not update `docs/context.md`. The OpenSpec repo rule asks for that update when a build step completes. Row 0.3's allowed paths forbid it, the same way 0.1 and 0.2 left that file alone. The metrics doc is the record.
- Not add a package. Scoring stays the existing pure `score_case` function.

The blueprint lists metrics this runner does not emit, and the same row forbids changing the runner. That conflict is closed here by recording the gap, not by widening the allowed paths. Subslice 0.4 inherits the gap and does not clear it.
