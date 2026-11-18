## Purpose

Runs the reasoner and critic beside the current planner on a sampled share of requests so quality, latency, and token cost can be compared without changing the trip the user receives.

## ADDED Requirements

### Requirement: Shadow runs only in the legal flag combination
A shadow pass MUST run only when `REASONING_LAYER_ENABLED` is false, `REASONING_SHADOW_SAMPLE_RATE` is greater than 0, and the request is selected. Selection MUST be a stable hash of session id, destination id, and whitespace-normalized request text, compared with the sample rate. The same inputs MUST select the same requests. A rate of 0 MUST select nothing. A rate of 1 MUST select every request. When the layer flag is true, the sample rate MUST NOT start a shadow pass.

#### Scenario: Defaults run no shadow
- **WHEN** the layer flag is false and the sample rate is 0
- **THEN** no reasoner call and no critic call are made for shadow

#### Scenario: The same request is selected again
- **WHEN** two generates share session id, destination id, and normalized text, and the sample rate selects that hash
- **THEN** both are selected, and a different text that hashes outside the rate is not selected

#### Scenario: Layer on does not shadow
- **WHEN** `REASONING_LAYER_ENABLED` is true and the sample rate is 1
- **THEN** no shadow pass runs

### Requirement: Shadow cannot change the response or persist a treatment
Shadow work MUST run on copies after the terminal SSE event. It MUST NOT call the emit callback. It MUST NOT change `itinerary`, `schedule`, `route`, `ranked_pois`, or `validation_result` on the state returned to the router. `save_from_state` MUST persist that returned control trip and MUST NOT persist a second trip for the shadow ranking. Shadow MUST NOT call the planner graph, a geocoder, or a routing provider. It MAY re-rank a copy of the candidates in memory.

#### Scenario: Shadow ranking is not the saved trip
- **WHEN** a sampled request finishes with a control itinerary and the shadow ranking orders places differently
- **THEN** the emitted `itinerary_done` body and the trip passed to `save_from_state` stay the control itinerary, and no second trip row is written

#### Scenario: Shadow does not emit
- **WHEN** a shadow pass runs
- **THEN** the SSE event list is the same list the control generation already produced

### Requirement: Shadow is budget-capped and outside the graph timeout
Shadow reasoner and critic calls MUST share `ORCHESTRATION_MAX_AGENT_INVOCATIONS` and the same per-call deadline as the live roles. They MUST run after `graph.ainvoke` has finished, outside `PLANNER_GENERATION_TIMEOUT_SECONDS`. A shadow timeout or error MUST NOT add `generation_timeout` and MUST NOT set `abort_triggered` on a generation that already succeeded. Client disconnect MUST cancel an in-flight shadow pass. A skipped shadow MUST record a named reason.

#### Scenario: Shadow failure keeps a successful generate
- **WHEN** the graph completed with `plan_complete` and the shadow call times out
- **THEN** the returned state is not marked `generation_timeout` or `abort_triggered` because of that timeout

#### Scenario: The invocation cap bounds shadow spend
- **WHEN** a sampled request runs shadow
- **THEN** the shadow pass makes at most `ORCHESTRATION_MAX_AGENT_INVOCATIONS` gateway calls and does not start a second planner tool loop

### Requirement: Shadow evidence is stored on the existing trace
A shadow pass MUST append `tool_trace` diagnostics entries named `experience_reasoner` and, when the critic runs, `itinerary_critic`. Those entries MUST NOT increment `tool_loop_count`. Token counts from the calls that actually ran MUST merge into the existing `token_usage` totals. No new `TripEvaluation` column and no new table are introduced. Flag-off, unsampled generates MUST append neither entry.

#### Scenario: An unsampled generate has no reasoning trace
- **WHEN** the layer flag is false and the request is not selected
- **THEN** `tool_trace` gains no `experience_reasoner` or `itinerary_critic` entry and `token_usage` is unchanged by this slice

#### Scenario: A sampled generate records the comparison
- **WHEN** a shadow pass accepts priorities and skips the critic for budget
- **THEN** the trace records the reasoner outcome, the skip reason, and the token totals include the reasoner call
