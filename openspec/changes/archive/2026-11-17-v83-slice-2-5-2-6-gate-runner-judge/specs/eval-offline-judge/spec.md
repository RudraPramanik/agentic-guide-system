## Purpose

Offline, sampled LLM judge scaffold that scores preference and narrative quality through the existing gateway, stays off the request path, and never overrides deterministic gate results.

## ADDED Requirements

### Requirement: Judge is offline, flagged, and sampled
The judge MUST run only from an offline evaluation entry point. It MUST NOT be imported by planner generate, tools, routers, or travel_engine modules. `EVALUATION_JUDGE_ENABLED` MUST default to false. When the flag is false, the judge MUST make no gateway calls. When the flag is true, the judge MUST judge at most a configured sample of cases and MUST NOT judge the full golden set by default.

#### Scenario: Flag off makes no judge call
- **WHEN** `EVALUATION_JUDGE_ENABLED` is false and the offline judge entry point is invoked
- **THEN** no LLM gateway call is made and no judgment files are required

#### Scenario: Request path does not import the judge
- **WHEN** architecture or import checks scan planner, tools, routers, and travel_engine
- **THEN** none of those modules import `src.evaluation.judge`

### Requirement: Judge calls go only through the LLM gateway
Judge model calls MUST use the existing `src/core/llm` gateway. The judge package MUST NOT import `litellm`, `groq`, or `openai`. Judge timeout MUST use `EVALUATION_JUDGE_TIMEOUT_SECONDS`, which MUST default to `15`.

#### Scenario: Judge uses the gateway
- **WHEN** the judge is enabled and scores one sample case
- **THEN** the call goes through the gateway and no provider SDK is imported from the judge package

#### Scenario: Timeout setting exists with default fifteen
- **WHEN** settings are loaded with no judge timeout override
- **THEN** `EVALUATION_JUDGE_TIMEOUT_SECONDS` is `15`

### Requirement: Judgments are schema-validated and versioned
Every judgment MUST validate against a closed output schema that includes pass/fail per rubric dimension, optional free-text, model identity, prompt version, and rubric version. An invalid model response MUST be rejected as a judgment schema failure. Prompt text and rubric text MUST be versioned artifacts stored with the judge, not anonymous inline strings that change silently.

#### Scenario: Valid judgment parses
- **WHEN** the model returns an object that matches the judgment schema with prompt and rubric versions
- **THEN** the judge accepts it and stores those versions with the judgment

#### Scenario: Invalid judgment is rejected
- **WHEN** the model returns an object missing a required dimension or version field
- **THEN** the judge rejects it as a schema failure and does not treat it as a calibrated score

### Requirement: Judge failure leaves deterministic eval unaffected
If the judge is unavailable, times out, returns an invalid schema, or raises, the offline runner MUST record `judge_unavailable` (or an equivalent named failure) for that sample and MUST leave deterministic case verdicts, gate pass rate, and gate exit code unchanged.

#### Scenario: Judge outage does not flip the gate
- **WHEN** deterministic cases all pass the gate and the judge call fails
- **THEN** the gate exit code stays zero and the run records `judge_unavailable` for the judge sample

#### Scenario: Deterministic fail still fails with judge off
- **WHEN** a non-quarantined case regresses and the judge is disabled
- **THEN** the gate still exits non-zero for that regression
