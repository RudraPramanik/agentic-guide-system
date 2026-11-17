## MODIFIED Requirements

### Requirement: chat_with_tools gateway contract
The project SHALL expose `async def chat_with_tools(messages, tools, tool_choice="auto", model=None) -> LLMToolResponse` in `src/core/llm/client.py` as the sole tool-calling LLM entry point.

The implementation MUST:
- When `LLM_REPLAY_MODE` is `off` or `record`, pass `tools` and `tool_choice` through to `litellm.acompletion`
- When `LLM_REPLAY_MODE` is `replay`, return the stored fixture and not call the provider
- Parse provider tool calls, and tool calls stored in a fixture, into a list of `{name, arguments_json}` on `LLMToolResponse.tool_calls`
- On content-only responses, return `tool_calls=[]` and set `content`
- Use the same tenacity retry contract as `chat_completion` for `Timeout` / `RateLimitError` when the mode is `off` or `record`
- Raise `WandrLLMError` after retries are exhausted (MUST NOT hang without timeout)
- Raise `WandrLLMError` with code `replay_miss` when the mode is `replay` and no fixture exists, without calling the provider

No second LLM gateway and no `litellm` imports outside `client.py` are allowed. `replay` MUST NOT change the `LLMToolResponse` fields.

#### Scenario: Tool call response is parsed
- **WHEN** `litellm.acompletion` returns a message with a tool call and `LLM_REPLAY_MODE` is `off`
- **THEN** `LLMToolResponse.tool_calls` contains the function `name` and `arguments_json` string

#### Scenario: Content-only response
- **WHEN** `litellm.acompletion` returns a message with content and no tool calls and `LLM_REPLAY_MODE` is `off`
- **THEN** `tool_calls` is empty and `content` is set from the message

#### Scenario: Exhausted retries raise WandrLLMError
- **WHEN** the provider fails until retries are exhausted and `LLM_REPLAY_MODE` is `off`
- **THEN** `chat_with_tools` raises `WandrLLMError` and does not hang without a timeout

#### Scenario: Replay does not call the provider
- **WHEN** `LLM_REPLAY_MODE` is `replay` and a fixture exists for the tool-calling payload
- **THEN** `chat_with_tools` returns that fixture's tool calls or content and `litellm.acompletion` is not called
