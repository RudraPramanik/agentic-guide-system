# Proposal: wire-langfuse-tracing-and-eval-harness

## Why

The system generates itineraries but cannot *measure* them. `TripEvaluation` records rich traces (`tool_trace`, fallbacks, timings), yet `token_usage` is always `{}` because `core/llm/client.py` discards `response.usage`, and the Langfuse tracer facade (`src/core/observability/tracing.py::get_tracer()`) is dead code with zero callers despite `langfuse==2.60.10` being pinned and keys declared in settings. Meanwhile `docs/next_version.md` Stage 3 promises "evaluation-driven polish" that has no eval infrastructure to drive it. This change lights up observability and builds a golden-dataset regression harness so future pipeline changes (including v7.0 hybrid search) can be validated against evidence, not vibes.

## What Changes

- **Token/retry capture in LLM gateway**: `chat_completion` / `chat_with_tools` / `embed_texts` in `src/core/llm/client.py` capture `response.usage` and retry counts; `PlannerService.generate()` threads them into `TravelState` so `TripEvaluation.token_usage` and `llm_retry_count` populate honestly for the first time.
- **Langfuse tracing wired**: `get_tracer()` facade gains callers — one trace per generation (started/ended inside `PlannerService.generate`, covering timeout/abort paths), spans per tool call derived from existing `ToolTraceEntry`s, generation spans per LLM call. Tracer failures are swallowed and logged once (fail-soft, mirroring `evaluation_write_failed`). No new packages; langfuse stays pinned at v2 line.
- **Offline eval harness**: new `evals/golden/<destination>/*.json` property-based cases (assertions on constraints, must-include places, `validation_passed`, readiness/fallback/tool-call bounds — never exact output strings), deterministic pure-Python scorers in `src/evaluation/scorers.py` (reusing `travel_engine.trip_validator.validate_trip`), and `scripts/run_evals.py` runner that replays cases through `PlannerService.generate()` with mocked routing, scores, writes run reports to `evals/runs/`, and diffs against a frozen baseline.
- **Docs blueprint**: `docs/next_version.md` gains a Part 2 section describing this work as staged stages with ship proofs (human-readable SSOT companion).

## Capabilities

### New Capabilities

- `llm-observability-tracing`: Trace/token instrumentation of the LLM gateway and planner generation lifecycle via the NoOpTracer/Langfuse facade — fail-soft contract, kill-switch by empty keys, token usage capture.
- `eval-golden-harness`: Offline golden-dataset evaluation harness — case schema, deterministic scorers, replay runner, baseline diffing, exit codes for CI gating.

### Modified Capabilities

- `p7-edit-evaluation`: `TripEvaluation.token_usage` and `llm_retry_count` change from "always empty/default" to "populated from actual LLM gateway responses" — a spec-level data-completeness behavior change.

## Impact

- **Code**: `src/core/llm/client.py` (usage capture + tracing wrap), `src/core/observability/tracing.py` (attribute helpers only), `src/planner/service.py` + `src/planner/graph/state.py` (thread token_usage/retry counts into state), `src/evaluation/service.py` (map new state fields — columns already exist).
- **New files** (pure additions, never imported by request path): `evals/golden/**`, `evals/runs/**`, `scripts/run_evals.py`, `src/evaluation/scorers.py`.
- **APIs**: No endpoint, schema, or tool-contract changes. `TripEvaluation` table unchanged (columns already exist). Frontend untouched.
- **Dependencies**: None added. `langfuse==2.60.10` already pinned (v2 API matches the facade; do NOT upgrade to v3 — it removed the `trace()` client API).
- **Runtime risk**: confined to the single LLM gateway module; all tracing wrapped fail-soft so observability can never fail a generation. With `LANGFUSE_*=""` (default) behavior is byte-identical to today via `NoOpTracer`.
- **AGENT.md constraints honored**: LLM only via `core/llm/client.py`; all env via `get_settings()`; no new packages; travel_engine purity untouched; evaluation records everything.

## Non-goals

- No HITL review/approval gate (deferred; implicit edit signals suffice for now).
- No LLM-as-judge scoring (evidence-gated follow-up once rule-based baselines exist).
- No Langfuse self-hosting deployment or dashboards-as-code.
- No LangSmith adoption.
- No changes to retrieval/search (v7.0 Part 1 scope).
