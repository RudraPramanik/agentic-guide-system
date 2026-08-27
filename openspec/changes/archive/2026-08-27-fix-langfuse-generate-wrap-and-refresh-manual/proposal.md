## Why

V2 claimed Langfuse is wired around `PlannerService.generate`, but the service only imports `start_generation_trace` / `end_generation_trace` / `emit_tool_spans_from_trace` and never calls them — so with keys set, tool spans stay dead and LLM generations are orphaned. Meanwhile the junior developer manual is frozen at P6.5 (2026-08-06) while `docs/context.md` is through P7 + v7 V0–V6.1, so onboarding docs contradict reality.

## What Changes

- Wire the existing Langfuse lifecycle helpers inside `PlannerService.generate()` (start → run → emit tool spans → end) on success, timeout, and recursion-abort paths — fail-soft unchanged.
- Strengthen tests so the wrap is asserted (not only “NoOp doesn’t crash”).
- Refresh the junior developer manual (`docs/app/documentation.md` + `docs/manual/*`) through current context (P7 complete + post-P7/v7 observability, golden harness, hybrid search as real where ✅).
- Light factual corrections: `docs/context.md` Langfuse claim accuracy; stale `docs/next_version.md` claims that `token_usage` is missing from `TravelState`; minimal `system.md` / `lld.md` status fixes if they contradict context.
- Update `docs/manual/06-maintenance.md` refresh log for this catch-up.

## Non-goals

- Evaluation HTTP API or in-app dashboards.
- Pushing golden-eval scores into Langfuse Datasets/Scores.
- In-app USD cost accounting (Langfuse pricing remains sufficient).
- Langfuse self-host / SDK upgrade to v3.
- Changing golden harness assertions, baselines, or hybrid retrieval behavior.
- New packages or env vars beyond documenting existing `LANGFUSE_*`.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `llm-observability-tracing`: Make the “one trace per generate” requirement enforceable — `PlannerService.generate` MUST invoke the tracing lifecycle helpers so tool spans nest under the parent trace when keys are configured.
- `developer-manual`: Catch-up refresh through P7 + post-P7/v7 (V0–V6.1) so through-step, module map, recipes, and stubs match `docs/context.md`.

## Impact

- **Code:** `src/planner/service.py`; `tests/planner/test_tracing_failsoft.py` (and/or a focused wrap test). Existing helpers in `src/core/observability/tracing.py` and gateway `safe_generation_span` stay as-is.
- **Docs:** `docs/app/documentation.md`, `docs/manual/01–06`, light touch `docs/context.md` / `docs/next_version.md` / optionally `docs/app/system.md` + `lld.md`.
- **APIs / deps:** None. Empty `LANGFUSE_*` remains NoOp; `langfuse==2.60.10` stays pinned.
- **AGENT.md:** Fail-soft tracing; no new packages; all env via `get_settings()`; do not invent evaluation HTTP APIs in the manual.
- **Related prior change:** Completes the unfinished V2.3 intent from archived `wire-langfuse-tracing-and-eval-harness` (task 3.2 marked done but callers missing).
