## ADDED Requirements

### Requirement: Planner generate SSE endpoint

The system SHALL expose `POST /api/v1/planner/generate` accepting `PlanRequest` and returning `text/event-stream` with events: preferences_done, phase_changed, tool_started, tool_done, validation_done, itinerary_done, clarification_needed, error.

#### Scenario: Stream completes on happy path

- **WHEN** a valid plan request is sent for a ready destination with LLM available
- **THEN** SSE stream emits tool events and final itinerary_done with days and stops including suggested_start_time

### Requirement: Generation timeout ceiling

The system SHALL wrap graph execution in `asyncio.wait_for` with `PLANNER_GENERATION_TIMEOUT_SECONDS` (default 45s).

#### Scenario: Timeout closes stream cleanly

- **WHEN** generation exceeds timeout
- **THEN** SSE error event is emitted and stream closes without hanging

### Requirement: Optional auth on generate

The system SHALL allow guest planning via `optional_auth` and auto-save trips for authenticated users.

#### Scenario: Guest can plan

- **WHEN** unauthenticated client posts to planner generate
- **THEN** generation succeeds and trip is associated with session_id
