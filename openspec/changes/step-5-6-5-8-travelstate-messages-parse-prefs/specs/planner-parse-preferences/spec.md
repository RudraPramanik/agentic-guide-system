## ADDED Requirements

### Requirement: parse_preferences is a fixed LLM bookend outside the tool loop
The project SHALL provide `async def parse_preferences(state) -> dict` in `src/planner/graph/nodes/parse_preferences.py`.

The node MUST call `chat_completion` from `src/core/llm/client.py` (NOT `chat_with_tools`) with a JSON response format to extract `{days, budget, interests, include_offbeat, include_trekking}` from `raw_input`. It is NOT part of the agent tool loop.

#### Scenario: Happy path parses preferences from mocked LLM JSON
- **WHEN** `chat_completion` returns valid JSON for input like `"3 days offbeat photography"`
- **THEN** the returned partial state includes `days=3` and interests reflecting photography and/or offbeat signals as specified by the node mapping rules

### Requirement: LLM failure applies deterministic defaults
On `WandrLLMError` OR bad/unparseable JSON, `parse_preferences` MUST apply defaults:
- `days=3`
- `budget="mid"`
- `interests=[]`
- `include_offbeat=False`
- `include_trekking=False`

and MUST increment `llm_retry_count`. The node MUST NOT abort generation solely because preference parse failed.

#### Scenario: WandrLLMError yields defaults
- **WHEN** `chat_completion` raises `WandrLLMError`
- **THEN** the result includes `days=3` and `llm_retry_count` greater than the input value

### Requirement: Interest mapping is vocab-aware and fail-soft
Obvious interest strings MUST be mapped toward `PLACE_TAG_VOCAB` when clear. Unknown interest strings MUST be kept (engine-safe: scoring may yield 0). The node MUST NOT import litellm directly.

#### Scenario: LLM only via core gateway
- **WHEN** the parse_preferences module source is inspected
- **THEN** it imports LLM helpers only from `src.core.llm.client` (or re-export thereof) and does not import `litellm`
