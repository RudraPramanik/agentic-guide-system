## Purpose

P5.7 compact agent messages: phase-aware `build_agent_messages` for `chat_with_tools` (allowed tools, hard rules, REPLAN expand guidance).

## Requirements

### Requirement: build_agent_messages produces phase-aware system prompt
The project SHALL provide `build_agent_messages(state: TravelState) -> list[dict]` in `src/planner/graph/messages.py`.

The system message MUST include:
- Role as a trip planner tool-using agent
- Current `agent_phase` and the allowed tool names for that phase only (from `PHASE_TOOLS`)
- Hard rules: never invent places, place IDs, coordinates, times, or stop order; call tools to act
- Compact state summary: days, interests, candidate/ranked counts, last validation errors, whether any day has `dropped_stops`
- Last 5 `tool_trace` entries only (not full history)

Tool schemas MUST NOT be inlined as free-text inventable tools; schemas remain the job of `get_tools_for_phase`.

#### Scenario: System message present for REPLAN state
- **WHEN** `build_agent_messages` is called with `agent_phase=REPLAN` and a minimal state
- **THEN** the returned list includes a message with `role=="system"` whose content references the REPLAN phase context

### Requirement: REPLAN prefers expand over drop when dropped_stops present
When the compact state summary detects `dropped_stops` on any day in `route` (or equivalent schedule/route structure), the system prompt MUST guide the agent to prefer `expand_poi_search` over `drop_weakest_stop`.

#### Scenario: dropped_stops triggers expand guidance
- **WHEN** state has `agent_phase=REPLAN` and `route` contains a day with non-empty `dropped_stops`
- **THEN** the system message content (case-insensitive) contains `expand_poi_search`

### Requirement: Missing optional fields do not raise
`build_agent_messages` MUST tolerate missing optional TravelState fields with safe defaults (empty lists / zero counts) and MUST NOT raise solely because optional working data is absent.

#### Scenario: Empty tool_trace still returns messages
- **WHEN** `build_agent_messages` is called with `tool_trace=[]` (or missing) and minimal other fields
- **THEN** it returns a valid non-empty messages list without raising
