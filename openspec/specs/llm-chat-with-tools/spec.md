## Purpose

P0 LLM tool-calling gateway: verify and test `chat_with_tools` / `LLMToolResponse` in `src/core/llm/client.py` (step 5.4) — sole litellm entry for agent tool loops.

## Requirements

### Requirement: chat_with_tools gateway contract
The project SHALL expose `async def chat_with_tools(messages, tools, tool_choice="auto", model=None) -> LLMToolResponse` in `src/core/llm/client.py` as the sole tool-calling LLM entry point.

The implementation MUST:
- Pass `tools` and `tool_choice` through to `litellm.acompletion`
- Parse provider tool calls into a list of `{name, arguments_json}` on `LLMToolResponse.tool_calls`
- On content-only responses, return `tool_calls=[]` and set `content`
- Use the same tenacity retry contract as `chat_completion` for `Timeout` / `RateLimitError`
- Raise `WandrLLMError` after retries are exhausted (MUST NOT hang without timeout)

No second LLM gateway and no `litellm` imports outside `client.py` are allowed.

#### Scenario: Tool call response is parsed
- **WHEN** `litellm.acompletion` returns a message with a tool call
- **THEN** `LLMToolResponse.tool_calls` contains the function `name` and `arguments_json` string

#### Scenario: Content-only response
- **WHEN** `litellm.acompletion` returns a message with content and no tool calls
- **THEN** `tool_calls` is empty and `content` is set from the message

#### Scenario: Exhausted retries raise WandrLLMError
- **WHEN** the provider fails until retries are exhausted
- **THEN** `chat_with_tools` raises `WandrLLMError` and does not hang without a timeout

### Requirement: Unit tests for chat_with_tools
The project SHALL provide `tests/core/test_llm_chat_with_tools.py` that mocks `litellm.acompletion` and covers tool-call parsing, content-only responses, and exhausted-retry → `WandrLLMError` (matching existing `chat_completion` test style where present).

#### Scenario: Pytest module passes
- **WHEN** `python -m pytest tests/core/test_llm_chat_with_tools.py -v` is run
- **THEN** all scenarios in this capability pass without live LLM network calls
