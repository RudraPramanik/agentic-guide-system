# ADR-007 — Evaluation gates, tolerances, and replay CI

## Context

Blueprint v8.3 §11 says deterministic dimensions gate and judge dimensions inform. Baselines change only through an explicit `--update-baseline` in a reviewed PR. CI evals use recorded LLM fixtures; live-model runs are scheduled and must not block pull requests on flakiness. §11.4 says a metric with unmeasured variance cannot gate. Slice 0 left generate latency, tokens, cost, and coherence variance unmeasured. Rows 2.1–2.4 shipped the golden schema, gateway replay, pure metrics, and property tests. The golden set is still the twelve Darjeeling cases. §11.2 asks for at least 24 cases across at least three destinations before Slice 2 is considered exited.

## Decision

Non-quarantined case pass/fail is the hard gate. Quarantined cases stay in the report and do not fail the gate by themselves. A regression prints `REGRESSION` and the case id and exits non-zero.

Tolerance bands hard-fail only when `evals/baselines/tolerances.json` lists that metric with a measured numeric baseline. Unmeasured metrics may appear on the run report and do not change the exit code. This change does not invent Slice 0 latency, token, cost, or coherence variances.

Pull requests and pushes to `main` run `python scripts/run_evals.py --destination darjeeling --replay`. A nightly workflow runs live mode without `--replay` and does not gate pull requests. If the live LLM secret is absent, the nightly job skips and says so. CI never passes `--update-baseline`.

The offline judge informs. It does not blend into the gate score, does not run on the request path, and is not promoted under §11.8 by this slice.

Shipping the gate runner does not claim the §11.2 minimum. At least 24 cases across at least three destinations remains a Slice 2 exit checklist item outside rows 2.5 and 2.6.

## Alternatives

Treat every §11.4 absolute threshold as a hard fail today. Rejected. Several of those metrics need labels or location types this suite does not assert, and unmeasured variance cannot gate.

Use `--fixtures-only` as the pull-request gate. Rejected. §11.1 and row 2.5 require replay on pull requests. Fixtures-only stays a local path.

Let the judge override a failing deterministic case. Rejected. ADR-004, N3, and N9 already forbid that.

## Consequences

`evals/baselines/tolerances.json` starts without hard-fail bands. A later measurement change may add a band in a reviewed pull request. The eval-gate job needs the services replay generate uses (database and Qdrant) and the committed replay fixtures. It does not need a live LLM key. The nightly job needs a live key and a prepared catalog; a failure there is a ticket, not a pull-request block.

## Migration and rollback

No migration and no deploy. Rollback is removing the eval-gate and nightly workflows and reverting the runner gate. `EVALUATION_JUDGE_ENABLED` defaults to false. Baselines stay in git.

## Status

accepted
