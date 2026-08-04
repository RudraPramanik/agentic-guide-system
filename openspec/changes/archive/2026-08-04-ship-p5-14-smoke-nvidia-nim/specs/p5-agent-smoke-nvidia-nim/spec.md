## ADDED Requirements

### Requirement: P5.14 live smoke runs via NVIDIA NIM LiteLLM provider
The project SHALL complete step 5.14 live validation by configuring the LiteLLM gateway through `LLM_MODEL`, `LLM_API_KEY`, and `LLM_API_BASE` only, using an NVIDIA NIM model id with the `nvidia_nim/` prefix (default preferred: `nvidia_nim/meta/llama-3.1-8b-instruct`; any free-tier `nvidia_nim/...` model MAY be substituted if smoke passes). `scripts/test_agent.py` MUST exit 0 with sections 1–8 passing. Unused alias env names (`NVIDIA_NIM_API_KEY`, `LLM_MODEL_NVIDIA`, etc.) MUST NOT be required by Settings. Completing smoke on NIM MUST NOT remove or hard-code against other LiteLLM providers for future runs.

#### Scenario: Settings resolve NIM after env remap
- **WHEN** local `.env` sets `LLM_MODEL` to a `nvidia_nim/...` id, `LLM_API_KEY` to a NIM key, and `LLM_API_BASE` to the NVIDIA integrate API base
- **THEN** `get_settings().LLM_MODEL` starts with `nvidia_nim/` and smoke section 1 passes

#### Scenario: Agent smoke completes on NIM
- **WHEN** Docker Postgres/Qdrant are up, Darjeeling is seeded+enriched+indexed, and NIM credentials are valid
- **THEN** `python scripts/test_agent.py` prints PASS for sections 1–8 (itinerary shape, tool_trace, evaluation row, import guards)

#### Scenario: Architecture stays provider-agnostic after ship
- **WHEN** an operator later remaps `LLM_*` to another LiteLLM provider (e.g. Gemini or Groq) without changing Python sources
- **THEN** planner nodes and tools still call only `chat_completion` / `chat_with_tools` and no module outside `src/core/llm/client.py` imports litellm

### Requirement: context.md stamps P5 complete after NIM smoke
After green `scripts/test_agent.py` and green `python -m pytest tests/ -v`, `docs/context.md` MUST mark Progress 5.1–5.14 ✅, set Next step → P6.1, list PlannerService among implemented modules, and keep planner HTTP `/planner/generate` and trips CRUD as P6 stubs.

#### Scenario: Context advances only after smoke green
- **WHEN** smoke and pytest have passed under the configured NIM provider
- **THEN** context Next step is P6.1 and 5.14 is ✅ — not left as “smoke pending”
