# Design — wire-langfuse-tracing-and-eval-harness

## Context

See proposal.md for motivation. Current state that shapes the approach:

- `src/core/observability/tracing.py` already implements the Null Object pattern (`get_tracer() -> Langfuse | NoOpTracer`, `flush_tracer()`), pinned `langfuse==2.60.10`, keys in settings — but has **zero callers**.
- `src/core/llm/client.py` is the sole litellm entry (`chat_completion`, `chat_with_tools`, `embed_texts`, tenacity `_llm_retry`) and **discards `response.usage`**; consequently `TripEvaluation.token_usage` is always `{}` and `llm_retry_count` never reflects reality.
- `PlannerService.generate()` already handles timeout/recursion-abort by constructing synthetic final states, and writes evaluation best-effort (soft-fail with `evaluation_write_failed`) — the fail-soft precedent to mirror.
- `TravelState` carries `token_usage` / `llm_retry_count` keys that nothing writes; `EvaluationService.record_generation` already reads them.
- Eval harness conventions exist: `scripts/test_p*_smoke.py` runners, `tests/travel_engine/fake_routing.py` deterministic routing, real-Postgres pytest fixtures.

## Goals / Non-Goals

**Goals:**
- Honest token/retry data flowing into `TripEvaluation` with zero schema change.
- Langfuse traces per generation via the existing facade, fail-soft everywhere.
- A golden-dataset regression harness runnable locally and CI-gateable.

**Non-Goals:**
- LLM-as-judge scoring (follow-up change once baselines exist).
- Langfuse self-hosting/deployment work.
- Any API/frontend/tool-contract change; any retrieval change (v7.0 Part 1 owns that).

## Decisions

### D1 — Facade wrapping over LiteLLM-native callback
Wrap the three gateway functions with `get_tracer().generation(...)` spans rather than setting `litellm.success_callback=["langfuse"]`.
- *Why*: keeps all observability behind the existing NoOpTracer abstraction (kill-switch = empty keys, testable with NoOpTracer, scoped to planner-relevant calls only). The native callback captures tokens automatically but introduces global mutable litellm state and logs every embed call in the app, not just planner flows.
- *Token capture still needed manually* — which D2 requires anyway.

### D2 — Usage capture inside the gateway, threaded through TravelState
Each gateway function returns usage alongside its existing payload without breaking signatures:
- `chat_completion` / `chat_with_tools`: attach a `usage` attribute (dataclass field on `LLMToolResponse`; lightweight wrapper or out-param pattern for `chat_completion` — prefer adding an optional return-object form only if signature change is unacceptable; default plan: new `LLMUsage` dataclass returned via a parallel `-> tuple[str, LLMUsage]`-style internal helper while public signatures stay compatible).
- Retry counting: increment via tenacity's retry action (`before_sleep` already exists as `_log_llm_retry` — extend it to bump a context-local counter).
- Threading: `agent_node` / `write_narrative` accumulate per-call usage into `state["token_usage"]` (sum prompt/completion/total) and `state["llm_retry_count"]`. `record_evaluation` already maps these keys — no repository/model change.
- *Alternative rejected*: reading usage from Langfuse traces back into Postgres — couples the ledger to the vendor.

### D3 — Trace lifecycle at service level, not router queue
Start the trace at the top of `PlannerService.generate()`, end it after `record_evaluation(final)` including timeout/abort branches (they build synthetic finals — end the trace there too).
- *Why not router*: the SSE queue drops `state_snapshot` args; service-level instrumentation sees full state and stays test-injectable.
- Tool spans derived post-hoc from `tool_trace` entries (name/ok/ms/fallback already recorded) rather than instrumenting each tool — zero changes to tool code.

### D4 — Fail-soft contract identical to evaluation writes
All tracer interaction wrapped in try/except that logs once per process (module-level flag) and continues. Mirrors `evaluation_write_failed`. With empty keys, `NoOpTracer` makes this path free.

### D5 — Property-based golden cases, deterministic scorers first
Case schema (versioned, per-destination under `evals/golden/<destination>/`):

```jsonc
{
  "id": "dar-001",
  "destination": "Darjeeling",
  "raw_input": "3 days, photography, sunrise spots",
  "must_include_places": ["Tiger Hill"],
  "assertions": {
    "validation_passed": true,
    "max_days": 3,
    "min_places_per_day": 3,
    "readiness_score_min": 0.6,
    "no_geo_fallback": true,
    "max_tool_calls": 10
  }
}
```

Scorers in `src/evaluation/scorers.py` are pure functions `(result, case) -> Verdict(pass, reasons)`; feasibility delegates to `travel_engine.trip_validator.validate_trip` (already pure). Runner `scripts/run_evals.py` replays via `PlannerService.generate(..., routing=FakeRoutingProvider(...))`, writes `evals/runs/<ts>-<sha>.json`, diffs vs `evals/baselines/<destination>.json`.
- *Why properties not snapshots*: LLM nondeterminism makes exact-output goldens flaky; properties are stable regression signals.
- *LLM-unavailable mode*: cases replayed against cached/fallback states still exercise deterministic assertions (constraints, validator, fallback flags) — matches the boot-without-LLM-key precedent.

### D6 — Baseline diff semantics
Exit non-zero only when a previously-passing case regresses. New passing cases are reported, not failures (encourages suite growth). `--update-baseline` is explicit; baseline files carry git SHA + case-set hash so stale baselines warn loudly.

## Resilience Contract

| Component | Retry | Timeout | Fallback |
|---|---|---|---|
| Tracer calls | none | SDK async batching | swallow + log-once; generation unaffected |
| Usage capture | none (in-response) | n/a | empty `LLMUsage` |
| Eval runner vs LLM | existing gateway retries apply | `PLANNER_GENERATION_TIMEOUT_SECONDS` | deterministic-only assertions still scored |

No new external I/O is introduced beyond the (optional, key-gated) Langfuse export the pinned SDK performs asynchronously.

## Risks / Trade-offs

- [Gateway is single point of failure] → tracing/usage code is additive try/except-wrapped; pinned tests assert unchanged return contracts before/after.
- [Langfuse v2 pin ages] → facade isolates vendor API; migration to v3 would touch one module. Do NOT upgrade casually (v3 removed `trace()` client API).
- [Golden cases drift from product evolution] → case schema versioned; baseline update is explicit and reviewed; stale-baseline warning via SHA/case-hash.
- [Runner needs live DB/Qdrant] → same dev-stack requirement as existing smoke scripts; documented, no new infra.
- [Trace volume cost] → one trace per generation (not per node); tool spans derived from already-recorded entries; no embed-call tracing outside planner flows.

## Migration Plan

1. Ship usage capture + state threading (behavior-visible only as honest evaluation data).
2. Wire tracer behind empty-by-default keys (prod unaffected until keys set).
3. Add harness + seed Darjeeling golden suite (~10–15 cases), freeze baseline.
4. Rollback: revert commit(s); no migrations involved; kill-switch = unset keys.

## Open Questions

None blocking. (Judge scoring, HITL gate, and Langfuse self-hosting are deliberately deferred follow-ups.)
