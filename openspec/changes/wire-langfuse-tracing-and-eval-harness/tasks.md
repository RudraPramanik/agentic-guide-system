# Tasks — wire-langfuse-tracing-and-eval-harness

## 1. Stage 1 — Token & retry capture in the LLM gateway

- [ ] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `src/core/llm/client.py` before coding; confirm current signatures and retry policy
- [ ] 1.2 Add `LLMUsage` dataclass (prompt_tokens, completion_tokens, total_tokens) in `src/core/llm/client.py`; capture from `response.usage` in all three gateway functions with silent degrade to empty usage when absent
- [ ] 1.3 Extend `_llm_retry` bookkeeping so retry attempts are countable per call (extend existing `before_sleep` hook; no behavior change to retry policy)
- [ ] 1.4 Add pinned tests: usage captured when provider returns it; empty-usage degrade; return contracts of all three functions unchanged (`tests/core/` style, mocked `litellm.acompletion`/`aembedding`)
- [ ] 1.5 Proof: `pytest tests/core -v` green

## 2. Stage 2 — Thread usage into state and evaluation

- [ ] 2.1 In planner agent/narrative nodes, accumulate per-call `LLMUsage` into `state["token_usage"]` (summed) and retry counts into `state["llm_retry_count"]`
- [ ] 2.2 Verify `EvaluationService.record_generation` maps the populated keys into `TripEvaluation.token_usage` / `llm_retry_count` (columns exist; adjust mapping only if keys mismatch)
- [ ] 2.3 Add test: generation with mocked LLM writes evaluation row with non-empty token_usage; zero-LLM-call path writes empty/zero values
- [ ] 2.4 Proof: `pytest tests/planner tests/evaluation -v` green; manual generate → check `trip_evaluations` row has real totals

## 3. Stage 3 — Wire Langfuse tracing (fail-soft)

- [ ] 3.1 Add small attribute helpers to `src/core/observability/tracing.py` only (no API change); add log-once swallow wrapper for tracer failures
- [ ] 3.2 Start/end one trace around `PlannerService.generate()` including timeout and recursion-abort branches (end trace with terminal outcome in synthetic-final paths)
- [ ] 3.3 Emit generation spans from gateway calls (model, tokens, latency, retries) and tool spans derived post-hoc from `tool_trace` entries — zero changes inside tools or graph nodes' logic
- [ ] 3.4 Test: with NoOpTracer (empty keys), generation results byte-identical to untraced run; simulated tracer exception does not fail generation
- [ ] 3.5 Optional manual proof: set Langfuse keys locally → one trace per generate with tool + LLM spans visible; unset → zero network traffic
- [ ] 3.6 Proof: `pytest tests/planner tests/core -v` green

## 4. Stage 4 — Golden eval harness

- [ ] 4.1 Create `evals/golden/darjeeling/` with case schema README + 10–15 property-based cases (constraints, must_include_places, validation_passed, readiness/fallback/tool-call bounds)
- [ ] 4.2 Implement `src/evaluation/scorers.py`: pure scorer functions `(result, case) -> Verdict`; feasibility delegates to `travel_engine.trip_validator.validate_trip`; unit tests for determinism and validator parity
- [ ] 4.3 Implement `scripts/run_evals.py`: load+validate cases (fail fast naming offender), replay via `PlannerService.generate(..., routing=FakeRoutingProvider...)`, write `evals/runs/<ts>-<sha>.json`
- [ ] 4.4 Implement baseline diffing: compare vs `evals/baselines/<destination>.json`, exit non-zero on regression, `--update-baseline` flag, stale-baseline warning via git SHA + case-set hash
- [ ] 4.5 Freeze Darjeeling baseline from a known-good run; document runner usage in script docstring
- [ ] 4.6 Proof: full run exits 0 against fresh baseline; deliberately break one assertion expectation → runner exits non-zero with named diff; restore

## 5. Docs & wrap-up

- [ ] 5.1 Write "Part 2" staged blueprint into `docs/next_version.md` mirroring stages 1–4 with ship proofs (human-readable companion, v7.0 style)
- [ ] 5.2 Update `docs/context.md` (Last updated, Next step, Progress, Implemented modules, stubs)

## 6. Guardrail compliance checklist (final)

- [ ] 6.1 No litellm/langfuse imports outside `src/core/llm/client.py` / `src/core/observability/tracing.py`
- [ ] 6.2 No new packages added to requirements*.txt
- [ ] 6.3 All new env via `get_settings()`; default-empty keys keep boot working without Langfuse
- [ ] 6.4 travel_engine untouched; evaluation write path still fail-soft; planner tool contracts byte-identical
- [ ] 6.5 `pytest tests/core tests/planner tests/evaluation -v` fully green
