## Purpose

Proposes non-negative priorities for places the retriever already returned, through the existing chat gateway, and skips cleanly when the model output cannot be trusted.

## ADDED Requirements

### Requirement: Reasoning settings default to the current planner
The settings object MUST expose `REASONING_LAYER_ENABLED` defaulting to false, `REASONING_SHADOW_SAMPLE_RATE` defaulting to 0.0, `ORCHESTRATION_MAX_AGENT_INVOCATIONS` defaulting to 2, `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` defaulting to 0, and `AGENT_REASONING_MODEL` and `AGENT_CRITIC_MODEL` defaulting to empty strings. An empty model setting MUST mean `LLM_MODEL`. The sample rate MUST be rejected unless it is between 0 and 1 inclusive. `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` MUST be rejected unless it is 0. `ORCHESTRATION_MAX_AGENT_INVOCATIONS` MUST be rejected when it is negative. These values MUST be read only through `get_settings()`.

#### Scenario: Defaults keep today's planner
- **WHEN** settings load with no reasoning variables set
- **THEN** the layer flag is false, the sample rate is 0, repair attempts are 0, and both role model strings are empty

#### Scenario: A non-zero repair attempt is rejected
- **WHEN** settings load with `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` set to 1
- **THEN** settings validation fails and the process does not start with a repair loop enabled

### Requirement: Reasoner output is priorities over known place ids only
The experience reasoner MUST accept only place ids that are already in the candidate set for that call. Each accepted item MUST be a priority of `high`, `medium`, or `low` for one id. An id that is not in the candidate set MUST be dropped and counted. A duplicate id MUST keep the first accepted item and drop the rest. An item that carries a latitude, longitude, order, time, price, or availability MUST be dropped. The reasoner MUST NOT add a place, coordinate, or schedule field to planner state. Omitted candidates MUST stay in the candidate set with no priority.

#### Scenario: An unknown id is dropped
- **WHEN** the model returns one priority for a candidate id and one priority for an id that was not retrieved
- **THEN** only the known id is accepted and the unknown id is counted as dropped

#### Scenario: Coordinates are not accepted as a priority
- **WHEN** a priority item includes a latitude and longitude
- **THEN** that item is dropped and no coordinate on the candidate is changed

#### Scenario: A missing candidate is not removed
- **WHEN** the model names only one of three retrieved candidates
- **THEN** all three candidates remain available to ranking and only the named one has a priority

### Requirement: Reasoner calls the chat gateway and is not a tool
The reasoner MUST call `chat_completion` and MUST NOT call `chat_with_tools`. The reasoning package MUST NOT import `litellm`, `groq`, or `openai`. The reasoner MUST NOT be added to the tool registry, MUST NOT appear in a phase tool allowlist, and MUST NOT increment `tool_loop_count`. User text, place names, tags, and provider descriptions MUST be passed as delimited untrusted data, not as instructions.

#### Scenario: A successful call uses chat completion
- **WHEN** the layer is enabled and the model returns a valid priority list
- **THEN** the call goes through `chat_completion` and the tool registry does not contain the reasoner

#### Scenario: The package does not import a provider SDK
- **WHEN** architecture checks scan `src/planner/reasoning/`
- **THEN** that package does not import `litellm`, `groq`, or `openai`

### Requirement: Reasoner failure skips without failing the trip
Malformed JSON, a schema mismatch, a gateway error, a missing replay fixture, or a deadline overrun MUST produce a skipped result with a named reason. A skipped result MUST be treated as no priorities. It MUST NOT raise out of ranking and MUST NOT abort the generation by itself. The attempt MUST record the model that was requested. A failure MUST NOT switch to a different model.

#### Scenario: Malformed JSON skips
- **WHEN** the model returns text that is not a valid priority payload
- **THEN** the result is skipped, the candidate set is unchanged, and ranking continues

#### Scenario: Gateway failure does not swap models
- **WHEN** `chat_completion` raises for the reasoner
- **THEN** the result is skipped with the requested model recorded and no second model is called

### Requirement: Reasoner calls are budgeted
A reasoner call MUST be wrapped in a deadline of `min(LLM_TIMEOUT_SECONDS, PLANNER_GENERATION_TIMEOUT_SECONDS // 5)`. Exceeding that deadline MUST skip the role. Reasoner and critic calls together MUST NOT exceed `ORCHESTRATION_MAX_AGENT_INVOCATIONS`. That cap MUST NOT count the existing agent-loop calls. When the cap is 1 and both roles are eligible, the reasoner MUST take the slot and the critic MUST be skipped. `PLANNER_GENERATION_TIMEOUT_SECONDS` MUST stay 45.

#### Scenario: A slow reasoner is skipped
- **WHEN** the reasoner call exceeds the per-call deadline
- **THEN** the result is skipped and the generation timeout setting is still 45 seconds

#### Scenario: One invocation leaves no critic slot
- **WHEN** the invocation cap is 1 and the reasoner call is made
- **THEN** the critic is not called
