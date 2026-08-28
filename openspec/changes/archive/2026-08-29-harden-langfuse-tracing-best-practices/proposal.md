## Why

Langfuse keys are now configured in `.env` and the tracer initializes as a live `Langfuse` client (not `NoOpTracer`), but a connectivity audit found gaps that prevent traces from closing correctly and from following Langfuse best practices: parent traces call a non-existent `trace.end()` API (fail-soft swallow), `LANGFUSE_BASE_URL` is ignored by `get_settings()`, session/user context is buried in metadata instead of first-class Langfuse fields, and LLM calls use manual generation spans instead of the recommended LiteLLM callback integration. Operators cannot reliably see complete generation lifecycles in the Langfuse UI until these are fixed.

## What Changes

- Fix parent trace closure to use the Langfuse v2 `trace.update()` API (no `trace.end()` on `StatefulTraceClient`).
- Add `LANGFUSE_HOST` (alias `LANGFUSE_BASE_URL`) to `get_settings()` and pass it to the Langfuse client constructor.
- Pass `session_id` and optional `user_id` as first-class trace fields on `PlannerService.generate()` (not metadata-only).
- Wire LiteLLM → Langfuse via the official callback handler in `src/core/llm/client.py`, keeping the existing fail-soft facade and removing duplicate manual generation spans where the callback covers them.
- Call `flush_tracer()` from FastAPI lifespan shutdown so short-lived processes and dev reloads do not drop batched events.
- Add a lightweight connectivity proof script or pytest that asserts live tracer type when keys are set and NoOp when empty.
- Document the optional-keys path in the developer manual (no behavior change when keys empty).

## Capabilities

### New Capabilities

_(none — hardening existing observability, not a new product surface)_

### Modified Capabilities

- `llm-observability-tracing`: Parent trace closure, host config, first-class session/user fields, LiteLLM callback integration, and shutdown flush become explicit requirements.

## Impact

- **Code:** `src/config.py`, `src/core/observability/tracing.py`, `src/core/llm/client.py`, `src/planner/service.py`, `src/main.py` lifespan, `.env.example`
- **Tests:** extend `tests/planner/test_tracing_failsoft.py` and/or add connectivity proof
- **Docs:** `docs/manual/05-how-to-change.md` (host env var, verify-traces recipe)
- **Dependencies:** no new packages — keep `langfuse==2.60.10` (v2 `trace()` API; v3+ removed it per project pin)
- **APIs:** none — internal observability only; empty keys remain NoOp byte-identical
- **AGENT.md:** LLM calls stay gateway-only; tracing stays in `core/observability/tracing.py`; fail-soft preserved

**Non-goals:** Langfuse SDK v3/v4 upgrade, self-hosted Langfuse deployment, Langfuse Datasets for golden evals, evaluation HTTP, cost USD math in Wandr, or real-time tool spans during execution (post-hoc tool_trace spans remain acceptable for MVP).
