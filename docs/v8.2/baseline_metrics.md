# Slice 0.3 baseline metrics

Read date: 2026-11-17. Source command: `python scripts/run_evals.py --destination darjeeling --fixtures-only`. The runner was not edited.

## 1. Retired live report

Copied from `evals/baselines/darjeeling.json` before any `--update-baseline` run.

| Field | Value |
|---|---|
| git sha | `3b58df2` |
| timestamp | `20260826T142922Z` |
| pass rate | 0.6666666666666666 (8 of 12 cases) |
| mode | `generate` on every case |
| case-set hash | `75f7af9c24c2` |

The on-disk copy of that run remains `evals/runs/20260826T142922Z-3b58df2.json`. This file is not the v8.3 baseline.

## 2. Fixtures-only pair

The two reports below were compared on `pass_rate` and on each case `id`, `passed`, `reasons`, and `mode`. Timestamps differ. Those stable fields match.

| Run | Path |
|---|---|
| First | `evals/runs/20261116T220232Z-dfcb8f0.json` |
| Second | `evals/runs/20261116T220235Z-dfcb8f0.json` |
| Freeze (`--update-baseline`) | `evals/runs/20261116T220307Z-dfcb8f0.json` |

| Field | Value |
|---|---|
| matched | yes |
| pass rate | 1.0 (12 of 12 cases) |
| mode | `fixture` on every case |
| git sha | `dfcb8f0` |
| designated baseline | `evals/baselines/darjeeling.json` (stable fields equal the pair) |

Failed case ids: none. This pass rate is a fixtures-only score. It is not a live generate result and it is not a latency or cost figure.

## 3. Unmeasured metrics

The fixtures-only report has no field for these. Each one is unmeasured. No stand-in number is recorded.

| Metric | Status |
|---|---|
| Invalid-trip rate | unmeasured |
| Duplicate rate | unmeasured |
| Coherence | unmeasured |
| Schedule feasibility | unmeasured |
| p50 latency | unmeasured |
| p95 latency | unmeasured |
| LLM calls per trip | unmeasured |
| Tokens per trip | unmeasured |
| Cost per trip | unmeasured |
| OSRM or geo fallback rate | unmeasured |
| Persistence failures | unmeasured |
