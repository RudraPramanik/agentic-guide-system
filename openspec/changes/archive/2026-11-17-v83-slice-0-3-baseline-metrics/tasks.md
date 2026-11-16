## 1. Preflight

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 row 0.3, this change's `proposal.md`, `design.md`, and `specs/s0-baseline-record/spec.md`. Confirm the only writes are `docs/v8.2/baseline_metrics.md` and, after a match, `evals/baselines/darjeeling.json`.
- [x] 1.2 Read the current `evals/baselines/darjeeling.json` and copy its sha, timestamp, pass rate, and mode into the retired-live section of the metrics doc before any `--update-baseline` run.

## 2. Fixtures-only pair

- [x] 2.1 Run `python scripts/run_evals.py --destination darjeeling --fixtures-only` twice. Do not pass `--update-baseline` on these two runs. Do not edit `scripts/run_evals.py`, `src/evaluation/scorers.py`, or `evals/fixtures/`.
- [x] 2.2 Diff the two new `evals/runs/` reports on `pass_rate` and on each case `id`, `passed`, `reasons`, and `mode`. Ignore `timestamp`, `git_sha`, and filename.

## 3. Freeze or halt

- [x] 3.1 When the stable fields match, run the same command a third time with `--update-baseline`. Confirm the written `evals/baselines/darjeeling.json` matches the pair on those stable fields and that `mode` is `fixture`.
- [x] 3.2 When the stable fields differ, do not run `--update-baseline`. Leave the existing baseline file unchanged and record the disagreeing case ids under the Halt heading.

## 4. Metrics doc

- [x] 4.1 Finish `docs/v8.2/baseline_metrics.md` with the four headings from design Decision 2, in that order. Heading 4 is omitted when the pair matched.
- [x] 4.2 Mark invalid-trip rate, duplicate rate, coherence, schedule feasibility, p50, p95, LLM calls, tokens, cost, OSRM or geo fallback rate, and persistence failures as unmeasured. Do not write zero or any other stand-in.

## 5. Verify

- [x] 5.1 Confirm the diff is only `docs/v8.2/baseline_metrics.md`, `evals/baselines/darjeeling.json` when the pair matched, and the new `evals/runs/` files the runner itself writes. No `src/` edit, no `scripts/` edit, no `docs/context.md` edit, no blueprint edit. Row 0.3's allowed paths forbid the context update the OpenSpec repo rule would otherwise ask for. Put the blueprint §19 completion report in the PR description, not in a new file.
