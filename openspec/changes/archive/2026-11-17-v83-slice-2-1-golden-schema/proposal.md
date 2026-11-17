## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 row **2.1**, and §11.1–§11.2) starts Slice 2 by making the golden set a validated schema before any ranking, location, or engine change. There is no `docs/steps/step*.md` for this row. Subslices 0.1–0.5 and 1.1–1.4 are archived. `docs/context.md` names Slice 2 as the next blueprint slice. The request "phase 2.0" maps to this row: the blueprint has no 2.0, and 2.1 is the first Slice 2 subslice.

Today `scripts/run_evals.py` accepts any non-empty `assertions` object and does not record a case type, labels, or a quarantine flag. A typo in an assertion key is scored as if it were absent. Later subslices cannot exclude a flaky case or group cases by the §11.2 composition until the loader rejects a bad file by name.

## What Changes

- Add a golden schema v2 loader under `src/evaluation/` that fails fast with a named error and the offending file name.
- Require `schema_version` 2, a closed `case_type`, a `labels` array, and a boolean `quarantined` flag. When `quarantined` is true, require a non-empty owner string, matching §11.2.
- Accept only the assertion keys the existing scorer already understands, with the types it already assumes. An unknown key or a wrong type is a named error.
- Migrate the twelve `evals/golden/darjeeling/*.json` files in place. Do not delete a case. Do not relabel a preference prompt as a location or failure case.
- No **BREAKING** HTTP, SSE, or persisted-trip change. A golden file that omits the new fields will no longer load. That is a dataset contract change, and the existing files are migrated in this change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `eval-golden-harness`: the golden case schema gains version, case type, labels, and quarantine, and a bad case fails with a named error instead of only a missing-field message.

## Impact

- **Work surface:** `src/evaluation/**`, `evals/golden/**`, `evals/golden/darjeeling/README.md`, `tests/evaluation/**`.
- **Call site outside the row's path cell:** `scripts/run_evals.py` replaces its inline field checks with the new loader and changes nothing else (no replay flag, no baseline logic, no generate path). The row's verify command is `pytest tests/evaluation -v`, and that command cannot see the script. This is the same kind of one-file wiring 1.1 used for `migrations/env.py`. No other file outside `evals/**` and `src/evaluation/**` is in scope.
- **No new package.** No `requirements.txt` change. No settings, no HTTP, no LLM call, so no new timeout or retry.
- **No impact on:** planner generate, SSE, trip persistence, scorers' verdict rules, baselines, or `docs/context.md`.
- **Downstream:** 2.2 owns record/replay, 2.3 owns new metrics, 2.4 owns engine property tests, 2.5 owns the regression gate and quarantine exclusion, 2.6 owns the offline judge. The §11.2 minimum of 24 cases is the Slice 2 exit gate, not this row.

## Non-goals

- No LLM record/replay, no `evals/replay/`, and no edit to `src/core/llm/client.py` (subslice 2.2).
- No new metric functions and no change to how `score_case` decides pass or fail (subslice 2.3).
- No property or metamorphic tests under `tests/travel_engine/` (subslice 2.4).
- No `--update-baseline` change, no CI workflow edit, and no exclusion of quarantined cases from the gate (subslice 2.5). The loader keeps a quarantined case in the loaded set and preserves the flag.
- No judge module and no `EVALUATION_JUDGE_ENABLED` setting (subslice 2.6).
- No new destinations and no new golden files. The twelve Darjeeling cases stay. Filling §11.2's composition counts waits until those case kinds exist.
- No edit to `docs/context.md`. Row 2.1's allowed paths forbid it, the same way Slice 1 left that file alone. The §19 completion report goes in the PR description.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Keep the loader free of LLM, network, and database I/O. It reads JSON and validates it.
- Add no package and no env read. `src/config.py` and `.env.example` stay untouched.
- Leave `travel_engine/`, the planner graph, and the LLM gateway untouched.
- Migrate existing cases when the new schema would reject them. Deleting a case is the row's stop condition.

Blueprint path notes, confirmed against the checkout rather than treated as a halt:

- The loader today is inline in `scripts/run_evals.py`. The permanent home is `src/evaluation/`, which is inside the allowed paths. The script keeps a single call.
- Tests belong in `tests/evaluation/**` because the verify command is `pytest tests/evaluation -v`. That directory already holds scorer tests and is outside the literal path cell, the same way 1.1 recorded `tests/planner/runs/**`.
