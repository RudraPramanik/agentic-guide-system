## Why

P5.1–5.13 are validated (PlannerService + tool-loop pytest), but step **5.14** cannot ship: live `scripts/test_agent.py` fails under Gemini free-tier `RateLimitError` → `generation_timeout`. Without a green (or properly documented) smoke + `docs/context.md` stamp, P6’s prerequisite gate stays closed. NVIDIA NIM via LiteLLM is already the blueprint/default provider path and has higher practical limits for local smoke.

## What Changes

- Point local LLM gateway env at **NVIDIA NIM** for this smoke run using the canonical trio only: `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` (ignore unused `NVIDIA_NIM_*` / `LLM_MODEL_NVIDIA` aliases — Settings does not load them).
- Prefer a free-tier-friendly LiteLLM model id, defaulting to blueprint: `nvidia_nim/meta/llama-3.1-8b-instruct` (swap allowed to another `nvidia_nim/...` free model if smoke tool-calling fails).
- **Preserve provider flexibility:** NIM is a *local config choice for smoke*, not a permanent architecture lock. Gemini / Groq / OpenAI / other LiteLLM providers remain valid by remapping the same three env vars — zero Python changes, planner/agent/tools/travel_engine unchanged.
- Document multi-provider examples in `.env.example` (NIM base URL + commented Gemini/other examples; placeholder keys only).
- Run `scripts/test_agent.py` (+ import guards); on green, mark **5.14 ✅** and set **Next step → P6.1** in `docs/context.md`.
- **Non-goals:** no LLM client code changes; no hard-coding `nvidia_nim` in `src/`; no HTTP `/planner/generate` (P6); no commits of `.env` / API keys; no removing Gemini as a viable future provider.

## Capabilities

### New Capabilities

- `p5-agent-smoke-nvidia-nim`: Complete P5.14 ship criteria — live agent smoke via a working LiteLLM provider (NIM for this run) + context.md P5 complete stamp, without narrowing the gateway to a single vendor.

### Modified Capabilities

- `planner-agent-smoke`: Clarify that live smoke MUST succeed with whatever LiteLLM provider `get_settings()` resolves, and that ongoing provider flexibility is env-only (`LLM_MODEL` / `LLM_API_KEY` / `LLM_API_BASE`) with no call-site coupling to NIM/Gemini/etc.

## Impact

- **Local `.env` only** (gitignored): remap `LLM_*` to NIM; never commit keys.
- **Docs:** `docs/context.md` after green smoke; optionally `.env.example` NIM base URL comment.
- **AGENT.md:** LLM only via `src/core/llm/client.py`; all env via `get_settings()`; SSE timeout still applies.
- **Step contract:** `docs/steps/step5.md` §5.14 — smoke + pytest before claiming P5 done.
- **Downstream:** Unblocks P6 (`docs/steps/step6.md` prerequisites) and archiving/applying planner API persistence work.
- **Risk:** NIM model must support `chat_with_tools` well enough for the agent loop within `PLANNER_GENERATION_TIMEOUT_SECONDS` (45s); fallback to phase-default tools may still produce a valid plan if tool_choice is flaky.
