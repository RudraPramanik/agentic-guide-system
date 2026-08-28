## 1. Config and host wiring

- [x] 1.1 Add `LANGFUSE_HOST` to `Settings` with default `https://cloud.langfuse.com` and `AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL")`
- [x] 1.2 Pass `host=settings.LANGFUSE_HOST` into `Langfuse(...)` in `get_tracer()`
- [x] 1.3 Update `.env.example` with `LANGFUSE_HOST` and note that `LANGFUSE_BASE_URL` is accepted as alias

## 2. Parent trace lifecycle fix

- [x] 2.1 Remove invalid `trace.end()` from `end_generation_trace()`; finalize parent via `trace.update(output=..., metadata=...)` only
- [x] 2.2 Extend `start_generation_trace()` to accept `session_id` and optional `user_id` as first-class Langfuse trace fields
- [x] 2.3 Wire `session_id` and available `user_id` from `PlannerService.generate()` into `start_generation_trace()`

## 3. LiteLLM callback integration

- [x] 3.1 Fetch current Langfuse v2 + LiteLLM callback docs (Context7 or langfuse.com) before coding
- [x] 3.2 When `_active_trace` is set and keys non-empty, attach trace-scoped LiteLLM Langfuse handler on gateway calls in `core/llm/client.py`
- [x] 3.3 Remove or gate manual `_emit_generation_span` to avoid duplicate generation observations when callback is active
- [x] 3.4 Confirm empty-key / NoOp path registers no callbacks and behavior unchanged

## 4. Shutdown flush and proof

- [x] 4.1 Call `flush_tracer()` in FastAPI lifespan shutdown (`main.py`)
- [x] 4.2 Extend `tests/planner/test_tracing_failsoft.py`: mock parent trace asserts `update` on end, not `end()` on parent; empty keys → NoOp
- [x] 4.3 Optional: add `scripts/prove_langfuse.py` — send one test trace when keys set, skip gracefully when empty

## 5. Docs and validation

- [x] 5.1 Update `docs/manual/05-how-to-change.md`: `LANGFUSE_HOST`, verify-traces recipe, Sessions view note
- [x] 5.2 Run `python -m pytest tests/planner/test_tracing_failsoft.py -v` and full suite if touched imports
- [x] 5.3 Manual proof (keys in `.env`): one generate → Langfuse UI shows parent trace with session, nested LLM generations, tool spans, terminal outcome — **connectivity via `scripts/prove_langfuse.py` OK**; full generate UI check left to operator
