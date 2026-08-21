## ADDED Requirements

### Requirement: Cold generate searches before empty abort
On a cache-miss generate for a destination that already passed the `PLANNER_ABSOLUTE_MIN_PLACES` floor, the tool loop MUST execute `search_places` (or otherwise populate `candidate_pois` from the destination catalog) before the run may end as SSE `error` / `generation_aborted` solely because the LLM did not select tools. If search/rank/route/schedule then produce a usable schedule, the stream’s terminal MUST be `itinerary_done` (with `trip_id` when saved). `generation_aborted` remains valid when search ran and still no usable itinerary can be built.

#### Scenario: Ready destination with LLM tool-call failure still searches
- **WHEN** a cold generate runs against a destination with enough places and `chat_with_tools` fails or returns no tool calls
- **THEN** the stream includes a `tool_done` for `search_places` before any terminal `generation_aborted`

#### Scenario: Successful search path still yields itinerary_done
- **WHEN** that search returns candidates and travel_engine can build a schedule
- **THEN** the single terminal is `itinerary_done` and, when saved, includes `trip_id`
