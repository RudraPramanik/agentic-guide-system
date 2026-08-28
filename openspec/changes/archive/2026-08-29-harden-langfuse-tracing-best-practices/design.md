## Context

See `proposal.md` — Why. V2 observability is shipped: `get_tracer()` / `NoOpTracer`, parent trace around `PlannerService.generate()`, manual `safe_generation_span` from `core/llm/client.py`, post-hoc tool spans from `tool_trace`, token usage in `TripEvaluation`. Keys in `.env` now initialize a live `Langfuse` client. Audit findings:

1. `StatefulTraceClient` (Langfuse v2) has no `.end()` — `end_generation_trace()` calls it inside fail-soft try/except, so parent traces never finalize correctly.
2. `LANGFUSE_BASE_URL` is in `.env` but not declared in `Settings`; Pydantic ignores it and the client uses the SDK default host.
3. `session_id` is only in trace `metadata`, not the Langfuse `session_id` field — Sessions view won't group.
4. Manual generation spans duplicate what LiteLLM's Langfuse callback can capture (Langfuse skill: prefer framework integrations).
5. No lifespan shutdown flush — batched events may be lost on reload/exit.

Pin stays `langfuse==2.60.10` — v3+ removed the `trace()` client API this facade uses (`docs/next_version.md`, `docs/app/system.md`).

## Goals / Non-Goals

**Goals:**

- Parent traces finalize correctly and appear complete in Langfuse UI.
- Host/region configurable via `get_settings()`.
- First-class `session_id` / optional `user_id` on generate traces.
- LiteLLM callback for automatic model + token capture under active parent trace.
- Shutdown flush in `main.py` lifespan.
- Proof test/script for live vs NoOp paths.

**Non-goals:**

- SDK v3/v4 migration, OpenTelemetry exporter, Langfuse Datasets, evaluation HTTP, USD cost math, real-time in-flight tool spans (post-hoc remains), or importing langfuse outside `tracing.py` / LLM gateway.

## Decisions

### 1. Fix parent trace closure with `update`, not `end()`

**Choice:** In `end_generation_trace()`, call `trace.update(output=..., metadata=...)` only; remove `trace.end()`. Keep `span.end()` / `generation.end()` for child observations (those methods exist on v2 clients).

**Alternatives:** Upgrade to Langfuse v3 `@observe` decorator — rejected (large migration, blueprint pin).

### 2. Host setting: `LANGFUSE_HOST` with `LANGFUSE_BASE_URL` alias

**Choice:** Add `LANGFUSE_HOST: str = "https://cloud.langfuse.com"` to `Settings`. Use Pydantic `Field(validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"))` so existing `.env` works. Pass `host=settings.LANGFUSE_HOST` to `Langfuse(...)`.

**Alternatives:** Rename env to only `LANGFUSE_HOST` — rejected (breaks user's current `.env`).

### 3. First-class session/user on trace start

**Choice:** Extend `start_generation_trace(session_id=..., user_id=...)` and pass to `tracer.trace(name=..., session_id=..., user_id=..., metadata={...})`. Keep `destination_id` in metadata. Wire from `PlannerService.generate()` — `session_id` already available; pass `user_id` when optional auth resolves an owner.

**Alternatives:** Metadata-only — rejected (Sessions/Users views need top-level fields).

### 4. LiteLLM Langfuse callback (v2 handler)

**Choice:** When tracer is live and `_active_trace` is set, attach Langfuse's LiteLLM callback/handler on each gateway call (research current v2 docs: `langfuse` package + litellm `success_callback` or trace-scoped handler from `trace.getNewHandler()`). Remove redundant `_emit_generation_span` for calls covered by the callback; keep fail-soft wrapper.

**Alternatives:** Keep manual spans only — rejected (Langfuse best practice, less drift on model/tokens).

**Guardrail:** Callback registration only inside `core/llm/client.py`; never import litellm elsewhere.

### 5. Shutdown flush

**Choice:** In `main.py` lifespan `yield` teardown, call existing `flush_tracer()` after DB/engine dispose.

**Alternatives:** Rely on SDK background thread only — rejected (dev reload drops events).

### 6. Connectivity proof

**Choice:** Extend `tests/planner/test_tracing_failsoft.py` with mocked Langfuse asserting `update` called on end (not `end` on parent). Optional `scripts/prove_langfuse.py` that sends one test trace when keys set — skip in CI when keys empty.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LiteLLM callback double-records if manual spans remain | Remove manual span when callback active; test with mock |
| Callback adds latency | Langfuse SDK batches async; fail-soft on callback errors |
| Concurrent generates share module-global `_active_trace` | Already existing limitation — document; future: contextvar (out of scope unless bug found) |
| Wrong host still connects to default EU | Explicit host in settings + proof script |

## Migration Plan

1. Ship code changes — backward compatible; empty keys unchanged.
2. Update `.env.example` with `LANGFUSE_HOST` comment (alias note).
3. Operators with keys: restart API, run one generate, verify trace in Langfuse UI (Sessions + nested generations).
4. Rollback: revert code; NoOp path unaffected.

## Open Questions

_(none blocking — user_id on generate may be guest-only today; pass when available, omit otherwise)_
