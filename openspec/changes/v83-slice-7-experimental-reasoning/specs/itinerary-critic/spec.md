## Purpose

Records an advisory critique of a finished itinerary without changing the trip, the validator result, or the repair loop.

## ADDED Requirements

### Requirement: Critic input is read-only
The critic MUST receive a copy of the request text, the search area when one is present, evidence refs already on the candidates, the canonical itinerary, and the deterministic findings. It MUST NOT receive a database session, a routing provider, or a tool executor. It MUST NOT write stops, order, times, geometry, or trip status.

#### Scenario: Critic notes do not change the itinerary
- **WHEN** the critic returns notes about a finished itinerary
- **THEN** the itinerary, schedule, route, and ranked places on the generation result stay as they were before the critic ran

### Requirement: Critic notes are advisory and versioned
Each accepted note MUST name one of `relevance`, `diversity`, or `narrative`, a stance of `pass`, `fail`, or `unknown`, and a message. The payload MUST include the model identity, the prompt version, and the rubric version. A note that sets a publish block, a repair action, or a finding severity MUST be dropped. A payload that is not valid JSON or that misses the version fields MUST skip the critic.

#### Scenario: A valid note is stored as a note
- **WHEN** the model returns one relevance note with stance `fail`, a prompt version, and a rubric version
- **THEN** that note is kept and it does not set `blocks_publish`

#### Scenario: A repair action is dropped
- **WHEN** a note includes a repair action or `blocks_publish` true
- **THEN** that note is not applied and no replan starts

### Requirement: Critic cannot override a critical finding
Deterministic findings and `validation_passed` MUST be unchanged by the critic. A critic note that disagrees with a critical finding MUST remain a note. The critic MUST NOT delete, downgrade, or clear a finding whose code is in the critical set. The critic package MUST NOT import `src.evaluation.judge`. `EVALUATION_JUDGE_ENABLED` MUST stay false for this change.

#### Scenario: A critic pass leaves a critical finding in place
- **WHEN** the validator has a critical `DUPLICATE_STOP` and the critic says the trip passes
- **THEN** `validation_passed` and the critical finding stay as the validator wrote them

#### Scenario: Judge outage is not this critic
- **WHEN** the critic call fails
- **THEN** the deterministic findings and the golden gate are unchanged and the offline judge is not invoked

### Requirement: Critic failure does not affect the published trip
A gateway error, timeout, malformed payload, or invocation-cap skip MUST record a named skip reason and MUST leave the emitted terminal event, the saved trip, and the validator result unchanged. The critic MUST NOT call the SSE emit callback.

#### Scenario: Critic timeout leaves the terminal event
- **WHEN** the critic exceeds its per-call deadline after `itinerary_done` was already emitted
- **THEN** no further SSE event is emitted and the saved itinerary is the one already emitted
