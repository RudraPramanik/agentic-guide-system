# ADR-013 — Reasoning-layer ship decision

## Context

Blueprint v8.3 §11.9 and §21 assign the Slice 7 ship decision to ADR-013. Rows 7.1–7.3 add a flag-gated experience reasoner, an advisory critic, and shadow sampling. `REASONING_LAYER_ENABLED` may become true only after the ship clauses pass on golden plus human-review evidence. The pre-registered human margin for this decision, fixed before treatment numbers were filled, is:

- human-rated quality improves by at least **+10 percentage points** pass rate, or by at least **+0.3** on a 5-point scale, and
- the confidence interval for that gain **excludes zero**.

Comparison entry point: `scripts/compare_reasoning.py`. Report path under `evals/runs/*-reasoning-compare.json`.

## Decision

**Stay off.** `REASONING_LAYER_ENABLED` remains `false` and `REASONING_SHADOW_SAMPLE_RATE` remains `0.0` in settings and `.env.example`.

Reasons recorded from the comparison:

1. No paired control-versus-treatment sheets exist under `evals/human_review/` (only the format example). Clause 2 of §11.9 is **not met**. Scores were not invented.
2. §4 cells for p50 latency, LLM calls/trip, tokens/trip, and cost/trip remain `[SET IN S0]` in `docs/v8.2/s0_targets.md`. Those clauses are **not met**.
3. Treatment replay fixtures (`*.reasoning.json`) are absent for golden cases. Missing fixtures fail closed without a live provider call. The deterministic both-sides comparison is therefore incomplete.
4. Generate p95 is still unmeasured against a live or latency-modeled baseline, so the p95 clause is **not met**.

This outcome is valid per §11.9. The layer may stay off indefinitely.

## Alternatives

1. **Enable the layer now.** Rejected. §11.9 requires every clause. Inventing human scores or filling `[SET IN S0]` cells would break N1 and the pre-registered margin rule.
2. **Enable shadow only in production.** Allowed later as an ops choice (`REASONING_LAYER_ENABLED=false`, sample rate > 0). Not part of this ADR's ship decision. Shadow still must not persist a treatment trip.

## Consequences

- Request-path ranking stays the deterministic travel engine when flags are at defaults.
- Shadow and live roles exist behind flags for further evidence collection.
- A later change may flip the layer flag only after a new comparison report shows every clause met and this ADR is superseded or amended with status `superseded`.

## Migration and rollback

No migration. Rollback is `REASONING_LAYER_ENABLED=false` and `REASONING_SHADOW_SAMPLE_RATE=0`. Cached reasoned entries use the `:reasoning-v1` key suffix and become unused when the flag returns to false.

## Status

accepted (stay off)
