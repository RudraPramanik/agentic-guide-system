## ADDED Requirements

### Requirement: Reasoning defaults do not change the generate stream
While `REASONING_LAYER_ENABLED` is false, `POST /api/v1/planner/generate` MUST emit the same SSE event names as today. `itinerary_done` MUST NOT gain a reasoning field, a priority list, or critic notes. `tool_done` MUST keep the fields `name`, `ok`, `code`, and `ms` only. A shadow pass MUST NOT add an event. The preference-cache key for that request MUST stay the flag-off key.

While `REASONING_LAYER_ENABLED` is true, event names and those `itinerary_done` and `tool_done` fields MUST stay the same. The itinerary body MAY differ because ranking used priorities. The cache key MUST use the reasoning suffix.

#### Scenario: Flag off adds no reasoning field
- **WHEN** a generate completes with `REASONING_LAYER_ENABLED` false and the sample rate 0
- **THEN** the SSE event names match the current contract and `itinerary_done` has no reasoning field

#### Scenario: Shadow adds no event
- **WHEN** a generate is sampled for shadow and the control path emits `itinerary_done`
- **THEN** the event list does not contain a shadow or critic event

#### Scenario: Layer on keeps the event names
- **WHEN** `REASONING_LAYER_ENABLED` is true and generate emits `itinerary_done`
- **THEN** the event name is still `itinerary_done` and its data fields are the itinerary, day count, and the existing optional trip id and accommodation label
