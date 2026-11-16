## Context

See proposal.md — Why. `scripts/run_evals.py` already loads `evals/golden/darjeeling`, scores with `src/evaluation/scorers.py` (pure, no I/O), and writes `evals/runs/<timestamp>-<sha>.json`. With `--fixtures-only` it reads `evals/fixtures/<id>.json` and does not call `PlannerService`. `--update-baseline` replaces `evals/baselines/darjeeling.json`. That file today is a live generate from `3b58df2` (pass rate 0.67, timestamp `20260826T142922Z`). Each report includes a timestamp, so two successful runs are not byte-identical. This change adds no external I/O: fixtures-only mode does not call the LLM, Qdrant, OSRM, or Nominatim, so there is no new timeout, retry, or fallback. `travel_engine/` is not edited.

## Goals / Non-Goals

**Goals:**

- A comparison rule that treats two fixtures-only reports as the same when pass rate, case id, passed, reasons, and mode match.
- A baseline file the existing runner will read on the next diff, written only after that match.
- One metrics doc that separates the measured pass rate from the row 0.3 metrics the runner cannot emit.

**Non-Goals:**

- Teaching the runner to emit latency, tokens, cost, or schedule metrics.
- Making every golden case pass. A repeated failure is a valid baseline.

## Decisions

### 1. Compare stable fields, then freeze once

Run `python scripts/run_evals.py --destination darjeeling --fixtures-only` twice. Diff the two new files under `evals/runs/` on `pass_rate` and on each case's `id`, `passed`, `reasons`, and `mode`. Ignore `timestamp`, `git_sha`, and the filename.

When they match, run the same command a third time with `--update-baseline`. The third report's stable fields MUST match the first two before that flag is used. The flag is the existing writer; this change does not add a second baseline path.

Alternative considered: copy one run JSON into `evals/baselines/` by hand. Rejected. The harness spec already defines `--update-baseline` as the only freeze switch.

Alternative considered: diff against the August live file and require exit code 0. Rejected. That file is a different mode. A fixtures-only case can fail the same way twice and still be reproducible. Reproducible here means the two fixtures-only reports agree, not that they agree with the live run.

### 2. Metrics doc headings

`docs/v8.2/baseline_metrics.md` uses these headings, in order:

1. Retired live report (sha `3b58df2`, timestamp `20260826T142922Z`, pass rate 0.67, mode `generate`)
2. Fixtures-only pair (the two run paths, whether they matched, measured pass rate, mode `fixture`)
3. Unmeasured metrics (the list in the spec, each marked unmeasured, no numeric stand-in)
4. Halt (present only when the pair disagreed: case ids that differed; baseline file not replaced)

### 3. Mismatch stops the freeze

On disagreement, do not pass `--update-baseline`. Write heading 4 and leave headings 2 and 3 honest about the failed pair. Do not edit `scripts/run_evals.py` or a fixture to force a match. That is the row 0.3 stop.

## Risks / Trade-offs

- [Replacing `darjeeling.json` changes what the next runner diff treats as "previously passing"] → Record the retired live identity in the metrics doc first, and leave `evals/runs/20260826T142922Z-3b58df2.json` untouched. Rollback is restoring the baseline file from git.
- [Fixtures-only pass rate is not live quality] → The doc states the mode. Subslice 0.4 must not multiply an unmeasured latency or cost by this pass rate.
- [A third run could theoretically diverge if a fixture file changed between runs] → Compare the third report's stable fields to the pair before accepting the written baseline. Fixtures are not edited by this change.

## Migration Plan

1. Draft the retired-live section from the current `evals/baselines/darjeeling.json` before any `--update-baseline`.
2. Run the fixtures-only command twice and compare stable fields.
3. On a match, run once with `--update-baseline` and confirm the written baseline's stable fields equal the pair.
4. Finish the metrics doc.

Rollback: `git checkout -- evals/baselines/darjeeling.json` and delete `docs/v8.2/baseline_metrics.md`. Run files under `evals/runs/` may remain; they are runner output, not the designated baseline.
