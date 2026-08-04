## ADDED Requirements

### Requirement: Live smoke provider is env-selected LiteLLM backend
Live execution of `scripts/test_agent.py` MUST use whatever provider `get_settings()` resolves from `LLM_MODEL` / `LLM_API_KEY` / `LLM_API_BASE`. Provider swaps for smoke (including NVIDIA NIM, Gemini, Groq, OpenAI-compatible endpoints) MUST NOT require code changes in `src/core/llm/client.py` or in planner graph/tools. The smoke script MUST continue to invoke `PlannerService.generate` directly (no HTTP router). Application features MUST remain provider-agnostic: no vendor-specific branches in nodes, tools, or travel_engine.

#### Scenario: Provider swap without code edit
- **WHEN** an operator changes only the `LLM_*` env trio to a working `nvidia_nim/...` model and re-runs smoke
- **THEN** generation calls go through the existing LiteLLM gateway and smoke sections that depend on the LLM can pass without modifying Python sources

#### Scenario: Flip back or to another vendor
- **WHEN** an operator later changes the same `LLM_*` trio to a different supported LiteLLM model string and matching key/base
- **THEN** the gateway and agent loop continue to function without requiring a new OpenSpec change for the swap itself

## MODIFIED Requirements

### Requirement: context.md marks P5 complete only after green gates
`docs/context.md` MUST be updated only after `scripts/test_agent.py` and `python -m pytest tests/ -v` pass. The update MUST:

- Set Next step → P6.1; Progress rows 5.1–5.14 ✅
- List implemented planner tools, graph, service bridge, evaluation service
- Keep trips CRUD / planner HTTP router as P6 stubs
- NOT claim P6 complete or register `/planner/generate` as a live endpoint

When the previous live blocker was provider rate limits, operators MUST re-run smoke against a viable LiteLLM provider (e.g. NVIDIA NIM) before applying the context stamp — documenting a permanent env blocker without attempting an alternate provider is insufficient for this ship. The context update MUST NOT imply the product is locked to that smoke provider.

#### Scenario: Green smoke proves itinerary shape
- **WHEN** smoke runs successfully against Darjeeling
- **THEN** sections 1–8 pass including day count, stop fields, tool_trace, and evaluation row

#### Scenario: HTTP generate still unregistered after P5
- **WHEN** the FastAPI app routes are inspected after this batch
- **THEN** no route path contains `planner/generate`

#### Scenario: Rate-limited provider does not skip the stamp
- **WHEN** smoke fails under one provider due to rate limits
- **THEN** context MUST NOT mark 5.14 ✅ until smoke passes under a working provider configuration (or an explicitly accepted documented blocker agreed outside this change)
