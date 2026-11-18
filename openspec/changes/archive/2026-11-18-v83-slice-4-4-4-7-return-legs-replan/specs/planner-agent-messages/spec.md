## MODIFIED Requirements

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
