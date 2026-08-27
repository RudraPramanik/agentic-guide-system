## Context

See proposal.md for motivation. Current code constraints:

- `src/core/observability/tracing.py` already exposes `start_generation_trace`, `end_generation_trace`, `emit_tool_spans_from_trace`, and `safe_generation_span` (fail-soft, log-once). `flush_tracer()` runs on lifespan shutdown.
- LLM gateway already emits generation spans via `safe_generation_span`; those attach to `_active_trace` when set, otherwise become orphan top-level generations.
- `PlannerService.generate()` imports the three lifecycle helpers but never calls them — the V2.3 gap.
- Token usage already flows `TravelState` → `TripEvaluation`; golden harness (`scripts/run_evals.py`) is separate offline accuracy tracking.
- Junior manual index is **Through step: P6.5** / **Last refreshed: 2026-08-06**; `docs/context.md` is through P7 + V6.1 (2026-08-26). Cadence: refresh on phase end or every 4–5 steps (`docs/manual/06-maintenance.md`).

## Goals / Non-Goals

**Goals:**
- One parent Langfuse trace per `generate()` when keys are set; tool spans nest; timeout/abort always end the trace.
- Tests that would have caught the missing wrap.
- Manual + light architecture/notes docs aligned with current context (P7 + shipped v7).

**Non-Goals:**
- Redesigning the tracer API, upgrading Langfuse SDK, or adding cost math in Wandr.
- Evaluation HTTP, Langfuse Datasets for golden cases, or CI job changes.
- Full rewrite of `system.md` / `lld.md` / `next_version.md` — only contradicting facts.

## Decisions

### D1 — try/finally lifecycle inside `PlannerService.generate` only
Start trace immediately after initial state is seeded; in `finally` (or equivalent always-run path): `emit_tool_spans_from_trace(final.get("tool_trace"))` then `end_generation_trace(outcome=..., metadata=...)`.
- *Why*: Matches archived V2 design (service-level, not router); covers timeout/recursion branches that build synthetic finals; avoids double-instrumenting tools.
- *Rejected*: Router-level wrap — SSE adapter lacks full state for tool spans and is harder to unit-test.
- *Rejected*: Context-var refactor of `_active_trace` in this change — out of scope; single-flight generate is the existing contract.

### D2 — Outcome labeling without new public API
Map terminal state to a small outcome string for `end_generation_trace` (e.g. `success` / `timeout` / `recursion_abort` / `clarification` / `error`) derived from existing flags (`abort_triggered`, `plan_complete`, errors list). Keep metadata minimal (destination_id, session_id optional) — no prompt dumps.
- *Why*: Enough for Langfuse filtering; avoids PII-heavy payloads.

### D3 — Assert wrap with mocks, keep NoOp identity test
Extend `tests/planner/test_tracing_failsoft.py` (or sibling): patch lifecycle helpers and assert `start` called once, `end` called once, `emit_tool_spans` called with the state’s tool_trace on success; existing NoOp “generate still completes” test remains.
- *Why*: Spec scenarios become regression-proof without requiring live Langfuse keys in CI.

### D4 — Manual catch-up pattern (same as prior P5/P6 refreshes)
Update index through-step + date; sync `03-module-map`, `04-imports-and-wiring`, `05-how-to-change`, orientation pointers; append `06-maintenance` log row. Source of truth for real-vs-stub remains `docs/context.md` — copy facts, do not invent APIs.
- Through-step wording: prefer explicit **P7 + V6.1** (or “post-P7 / V6.1”) rather than inventing a fake step id.
- How-to recipes: P7 smoke, optional Langfuse keys, `run_evals.py`; keep evaluation HTTP stub callout.

### D5 — Doc honesty for Langfuse claim
Update `docs/context.md` V2 / Implemented-modules notes only after the wrap lands in the same change (or in the same PR session), so agents are not told the wrap is done while still missing. Fix `docs/next_version.md` stale “token_usage not in TravelState” claim (mark superseded or correct in place).

## Resilience Contract

| Component | Retry | Timeout | Fallback |
|-----------|-------|---------|----------|
| Trace start/end/tool spans | none | SDK batching | swallow + log-once; generate unaffected |
| Empty Langfuse keys | n/a | n/a | `NoOpTracer` — byte-identical generate path |
| Manual refresh | n/a | n/a | If unsure real vs stub, read file content / context — never invent evaluation HTTP |

## Risks / Trade-offs

- **[_active_trace is process-global]** → Concurrent overlapping `generate()` in one worker could cross-attach spans. Mitigation: accept existing design for this fix; document as known limitation; do not expand scope to contextvars unless a follow-up change.
- **[Manual drift again]** → Cadence already in rules; this catch-up closes the gap through V6.1 only.
- **[Over-documenting deferred V6.2/V6.3]** → Explicitly keep them deferred/stub in the manual per context.

## Migration Plan

1. Land code wrap + tests (empty keys: no behavior change in prod).
2. Refresh docs in the same change.
3. Optional manual proof: set Langfuse keys locally → one nested trace per generate.
4. Rollback: revert service wrap; docs can stay (they would again overstate until re-fixed) — prefer revert both or note honesty.

## Open Questions

_(none — scope locked to wrap + junior-doc catch-up)_
