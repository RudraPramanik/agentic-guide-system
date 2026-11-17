## Purpose

Record and replay LLM gateway calls from fixtures so an eval run can repeat without a live provider, and a missing fixture fails by name instead of calling the network.

## Requirements

### Requirement: Replay mode defaults off
`LLM_REPLAY_MODE` MUST exist on settings and MUST default to `off`. The only legal values are `off`, `replay`, and `record`. Any other value MUST be rejected when settings load, before a gateway call. `off` MUST keep today's provider calls for chat completion, tool calling, and embeddings. The mode MUST be read through settings. Callers MUST NOT read or write process environment variables to select it.

#### Scenario: Default mode calls the provider
- **WHEN** `LLM_REPLAY_MODE` is `off` and a gateway chat call runs
- **THEN** the provider is invoked and no fixture file is required

#### Scenario: Unknown mode fails at load
- **WHEN** settings load with `LLM_REPLAY_MODE` set to `live`
- **THEN** settings loading fails before any gateway call

### Requirement: Replay returns the stored response and does not call the provider
When the mode is `replay`, each of chat completion, tool calling, and embeddings MUST return the stored fixture for that call and MUST NOT call the provider, sleep for a retry, or require an API key. The identity of a call MUST be the operation, the model, and the canonical payload. Timestamps and retry counts MUST NOT change which fixture is chosen. Two calls with the same identity MUST return the same content. Tool-calling fixtures MUST return the same tool-call names and argument strings. Embedding fixtures MUST return the same vectors. A tool-calling fixture MUST use the existing tool-call shape.

#### Scenario: Second replay matches the first
- **WHEN** the same chat payload is sent twice in `replay` and a fixture exists
- **THEN** both results have identical content and the provider is not called

#### Scenario: Tool-call fixture keeps the parse shape
- **WHEN** a tool-calling fixture stores one tool call
- **THEN** the returned tool call has the same name and argument string as the fixture

#### Scenario: Embedding replay matches vectors
- **WHEN** the same embedding input is sent twice in `replay` and a fixture exists
- **THEN** both results are the same vectors and the provider is not called

### Requirement: A missing replay fixture is a named failure
When the mode is `replay` and no fixture exists for that call identity, the gateway MUST raise the project's LLM error with code `replay_miss` and MUST include the fixture identity in the message. It MUST NOT call the provider and MUST NOT return empty content as a success.

#### Scenario: Missing chat fixture fails by code
- **WHEN** a chat payload has no fixture and the mode is `replay`
- **THEN** the call raises the LLM error with code `replay_miss` and the provider is not called

### Requirement: Record writes a fixture after one provider call
When the mode is `record`, the gateway MUST call the provider once under the existing timeout and retry policy, write one fixture for that call identity, and return the provider result. A later `replay` of the same identity MUST return that stored result and MUST NOT call the provider. Record MUST NOT run while the mode is `replay`.

#### Scenario: Record then replay skips the provider
- **WHEN** a payload is sent once in `record` and then the same payload is sent in `replay`
- **THEN** the provider is called only on the record, a fixture exists, and the replay content equals the recorded content

### Requirement: Provider SDK stays inside the gateway
The replay hook MUST live in the existing LLM gateway module. No other module MUST import the provider SDK to read or write fixtures. Fixture files MUST live under `evals/replay/`.

#### Scenario: Fixture read does not import the provider SDK outside the gateway
- **WHEN** replay loads a fixture
- **THEN** the provider SDK import remains only in the gateway module
