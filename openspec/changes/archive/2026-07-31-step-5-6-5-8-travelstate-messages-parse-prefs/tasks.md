## 1. Prep

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step5.md` steps 5.6–5.8 before coding
- [x] 1.2 Confirm 5.1–5.5 modules are real (registry, orchestration, chat_with_tools tests); graph files are still stubs

## 2. Step 5.6 — langgraph + TravelState

- [x] 2.1 Install a candidate `langgraph` version; run trivial 2-node `StateGraph` with conditional edge asserting `config["configurable"]["tool_context"]` sentinel round-trip
- [x] 2.2 Pin exact `langgraph==X.Y.Z` in `requirements.txt` with why-comment (never `>=`)
- [x] 2.3 Implement `src/planner/graph/state.py` — `TravelState` TypedDict with blueprint fields; document last-write-wins list fields; FORBIDDEN: `db`, `routing`, `ToolContext`, sessions, httpx
- [x] 2.4 Run step 5.6 ✅ validations (type hints exclude `db`/`routing`; langgraph import; hello-world configurable passthrough)

## 3. Step 5.7 — agent messages

- [x] 3.1 Implement `src/planner/graph/messages.py` — `build_agent_messages(state)` with phase, `PHASE_TOOLS` names, hard rules, compact summary, last 5 `tool_trace` entries
- [x] 3.2 Include REPLAN guidance: if any day has `dropped_stops` → prefer `expand_poi_search` over `drop_weakest_stop`
- [x] 3.3 Tolerate missing optional fields (safe defaults; must not raise)
- [x] 3.4 Run step 5.7 ✅ validation snippet (`expand_poi_search` in system text for REPLAN + dropped_stops)

## 4. Step 5.8 — parse_preferences

- [x] 4.1 Implement `src/planner/graph/nodes/parse_preferences.py` — `chat_completion` + JSON response_format only (not `chat_with_tools`); map interests toward `PLACE_TAG_VOCAB` when obvious
- [x] 4.2 On `WandrLLMError` or bad JSON: defaults (`days=3`, `budget="mid"`, `interests=[]`, offbeat/trekking false) + increment `llm_retry_count`; never abort solely on parse fail
- [x] 4.3 Run step 5.8 ✅ failure path (mocked `WandrLLMError` → defaults) and mocked happy-path JSON assert
- [x] 4.4 Confirm no live LLM key is required for these proofs (mocks only)

## 5. Verification + context

- [x] 5.1 Run targeted import/snippet checks from 5.6–5.8; ensure existing `pytest` suite still green (`python -m pytest tests/ -v` or planner+core subset if full suite is slow)
- [x] 5.2 Update `docs/context.md`: Progress 5.6–5.8 ✅; Implemented modules for `graph/state`, `messages`, `parse_preferences` + langgraph note; Next step → 5.9; keep agent/executor/builder/service/HTTP as stubs
