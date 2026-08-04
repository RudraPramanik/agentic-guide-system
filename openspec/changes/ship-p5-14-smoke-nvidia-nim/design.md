## Context

P5 tool-loop agent and `PlannerService.generate` are real; `scripts/test_agent.py` exists. Live smoke under `gemini/gemini-2.0-flash` hits free-tier rate limits and burns `PLANNER_GENERATION_TIMEOUT_SECONDS` (45s) on retries. LiteLLM already routes via `LLM_MODEL` / `LLM_API_KEY` / `LLM_API_BASE` in `src/core/llm/client.py`. Local `.env` currently keeps Gemini on the canonical trio while unused `NVIDIA_NIM_*` / `LLM_MODEL_NVIDIA` aliases sit ignored by Settings. Step contract: `docs/steps/step5.md` §5.14. Guardrails: `AGENT.md` (LLM gateway only; env via `get_settings()`).

## Goals / Non-Goals

**Goals:**

- Unblock P5.14 by running smoke against NVIDIA NIM with higher practical quota.
- Use env-only provider swap (no gateway code changes).
- Keep the architecture **provider-agnostic**: NIM for this smoke does not freeze the stack to one vendor.
- On green smoke + pytest, stamp `docs/context.md` P5 complete → Next P6.1.

**Non-Goals:**

- Changing `chat_completion` / `chat_with_tools` implementations.
- Hard-coding provider names in planner nodes, tools, or travel_engine.
- P6 HTTP SSE / trips CRUD.
- Committing secrets or rewriting Alembic (provider config is `.env`, not `alembic/env.py`).
- Permanently deleting Gemini (or any other provider) as a valid LiteLLM option.

## Decisions

1. **Canonical env trio only**  
   Map NIM credentials onto `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`. Do not add Settings fields for `NVIDIA_NIM_*`.  
   *Alternatives:* teach Settings to alias `NVIDIA_NIM_API_KEY` → rejected (extra surface; blueprint says swap model env only).

2. **Default smoke model**  
   `nvidia_nim/meta/llama-3.1-8b-instruct` (blueprint / `.env.example` default; generally solid for tool calling).  
   *Alternatives:* `nvidia_nim/mistralai/mistral-medium-3.5-128b` (user NIM pick) — allowed fallback if llama id unavailable on the account. Any other free `nvidia_nim/...` model is fine if smoke sections 3–6 pass.

3. **API base**  
   Set `LLM_API_BASE=https://integrate.api.nvidia.com/v1` for NIM (empty base is Gemini/OpenAI-default path). Document in `.env.example` as a comment/example value.

4. **Ship gate order**  
   Docker up → confirm `get_settings().LLM_MODEL` starts with `nvidia_nim/` → `python scripts/test_agent.py` → pytest if not already green this session → update `docs/context.md` only on success.

5. **No code path for provider — Gateway Pattern stays intact**  
   Callers (`parse_preferences`, `agent_node`, `write_narrative`, tools) only use `chat_completion` / `chat_with_tools`. They never import litellm or know the vendor. Resilience stays: litellm timeouts/retries + PlannerService `wait_for` + settings-derived `recursion_limit`. Failures remain fail-loud section headers in smoke.

6. **Flexibility contract (locked)**  
   Switching providers later = remap `LLM_MODEL` (+ key/base as needed). Features (phase tools, graph, evaluation, smoke sections) MUST keep working across providers that support chat + tool calling. Provider-specific quirks are handled by existing fallbacks (prefs defaults, agent nudge → phase-default tools, narrative templates) — not by forking architecture.

## Risks / Trade-offs

- [Accidental NIM lock-in via code or docs] → Mitigation: artifacts + `.env.example` state multi-provider; apply MUST not put `nvidia_nim` literals in `src/` beyond existing defaults in `config.py` / example strings.
- [NIM model lacks reliable tool_choice] → Mitigation: agent nudge + phase-default tools; try alternate free `nvidia_nim/...` model; smoke still requires non-empty tool_trace and valid schedule.
- [NIM latency > 45s wall] → Mitigation: reduce retry pressure (healthy key/quota); optionally raise `PLANNER_GENERATION_TIMEOUT_SECONDS` locally for smoke only (document if used); do not weaken production defaults in committed config without explicit ask.
- [Secrets in chat/history] → Mitigation: never write keys into OpenSpec artifacts or commits; rotate if exposed.
- [False “P5 done” without smoke] → Mitigation: context update is last task and blocked on section PASS.

## Migration Plan

1. Edit local `.env` (gitignored): point `LLM_*` at NIM; comment Gemini as fallback.
2. Refresh `.env.example` with NIM example **and** commented alternate provider examples (Gemini/Groq/OpenAI-style) so flexibility stays obvious.
3. Run smoke; on failure diagnose provider vs seed vs timeout.
4. Update `docs/context.md`; archive this change after apply.

Rollback: restore Gemini (or prior) values on `LLM_*` trio.

## Open Questions

- None blocking — model id may be swapped at apply time if the first NIM model is unavailable on the free tier.
