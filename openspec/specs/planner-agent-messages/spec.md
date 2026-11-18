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
When the compact state summary detects `dropped_stops` on any day in `route` (or equivalent schedule/route structure), and the travel-engine V2 mode is off, the system prompt MUST guide the agent to prefer `expand_poi_search` over `drop_weakest_stop`.

When the travel-engine V2 mode is on, that generic preference MUST NOT override a mapped repair. The system prompt MUST name the single legal `suggested_action` selected for this replan (`reoptimize_routes`, `drop_weakest_stop`, or `expand_poi_search`) when planner state has one. It MUST include each non-empty `dropped_stops` reason string from the route days. It MUST NOT name `accept_partial` as that mapped repair. It MUST NOT name a tool outside the REPLAN phase list.

#### Scenario: dropped_stops triggers expand guidance
- **WHEN** state has `agent_phase=REPLAN`, the travel-engine V2 mode is off, and `route` contains a day with non-empty `dropped_stops`
- **THEN** the system message content (case-insensitive) contains `expand_poi_search`

#### Scenario: Flag-on prompt names the mapped tool and the drop reason
- **WHEN** state has `agent_phase=REPLAN`, the travel-engine V2 mode is on, `v2_findings` includes one finding whose `suggested_action` is `drop_weakest_stop`, and a route day has a dropped stop whose reason is `exceeded_max_daily_travel`
- **THEN** the system message contains `drop_weakest_stop` and `exceeded_max_daily_travel`

#### Scenario: Flag-on prompt does not invent a tool
- **WHEN** state has `agent_phase=REPLAN`, the travel-engine V2 mode is on, and every `suggested_action` is null or not one of the three repair tools
- **THEN** the system message does not instruct a tool name outside `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, and `accept_partial`

### Requirement: Missing optional fields do not raise
`build_agent_messages` MUST tolerate missing optional TravelState fields with safe defaults (empty lists / zero counts) and MUST NOT raise solely because optional working data is absent.

#### Scenario: Empty tool_trace still returns messages
- **WHEN** `build_agent_messages` is called with `tool_trace=[]` (or missing) and minimal other fields
- **THEN** it returns a valid non-empty messages list without raising
