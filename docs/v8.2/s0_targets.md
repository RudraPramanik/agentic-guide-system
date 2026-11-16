# Slice 0.4 targets

Restatement of blueprint v8.3 §4 for later slices. The blueprint file `docs/steps/wandr_blueprint_version8.md` was not edited. Row 0.4 may write only `docs/v8.2/**`.

Numbers come only from `docs/v8.2/baseline_metrics.md`. The fixtures-only golden pass rate there is 1.0 (12 of 12 cases, mode `fixture`, sha `dfcb8f0`). That figure is a pass rate. It is not a latency, token, call, or cost baseline.

## Targets

| Target | Value | Gate | Source |
|---|---|---|---|
| Generate p95 latency | ≤ 45 s (`PLANNER_GENERATION_TIMEOUT_SECONDS`). Measurement: not measured. | Hard; never raised to make a feature fit | unmeasured |
| Generate p50 latency | ≤ baseline × 1.10 `[SET IN S0]` | Release gate | unmeasured |
| LLM calls per trip | ≤ baseline + 2 `[SET IN S0]` | Release gate for S7 | unmeasured |
| Tokens per trip | ≤ baseline × 1.25 `[SET IN S0]` | Release gate for S7 | unmeasured |
| Cost per trip | ≤ baseline × 1.25 `[SET IN S0]` | Release gate for S7 | unmeasured |
| Published trips with critical finding | 0 | Hard | blueprint hard gate |
| Duplicate stops in published trips | 0 | Hard | blueprint hard gate |
| Duplicate trips from retry/reconnect | 0 | Hard | blueprint hard gate |
| Golden-suite pass rate (deterministic assertions) | 100% of non-quarantined cases | Hard | `baseline_metrics.md` fixtures-only pass rate 1.0, as a pass rate only |

## Halt

p95 is not measured, so the row 0.4 stop "halt if p95 is already over 45 seconds" cannot be evaluated. This file does not claim the ceiling was met or missed.

The blueprint verify line "targets table has no placeholders" is unmet. The four `[SET IN S0]` cells above stay placeholders because p50, LLM calls, tokens, and cost are unmeasured. Filling them would invent the release gate.

Slice 3 does not start on these four gates until a later change, one whose allowed paths include measurement, reports a measured baseline for each of them.
