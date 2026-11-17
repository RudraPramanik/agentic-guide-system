# Golden eval cases — Darjeeling

Property-based cases only (never exact narrative strings or place orderings).

Schema version: `2` (integer).

Required fields per case:

- `schema_version` — integer `2`
- `id` — stable non-empty case id (`dar-NNN`)
- `destination` — non-empty human name
- `raw_input` — non-empty planner prompt
- `case_type` — one of:
  - `landmark_vs_city`, `ambiguous_name`, `map_pin_radius`, `neighborhood_or_address`
  - `sparse_data`, `multi_day`, `duplicate_prone`, `routing_failure`
  - `llm_unavailable`, `over_travel_budget`, `unknown_opening_hours`
  - `guide_suggestion`, `itinerary_preference`
- `labels` — array of non-empty strings; empty array is valid; duplicates are invalid
- `quarantined` — boolean. `false` omits `quarantine_owner`. `true` requires a non-empty `quarantine_owner`. A quarantined case still loads.
- `assertions` — non-empty object using only:
  - `validation_passed` (boolean)
  - `max_days` (integer)
  - `min_places_per_day` (integer)
  - `readiness_score_min` (number)
  - `no_geo_fallback` (boolean)
  - `max_tool_calls` (integer)

Optional fields:

- `destination_id` — non-empty string when present
- `must_include_places` — array of non-empty names when present

These twelve files are `itinerary_preference` with `labels` `["darjeeling"]` and `quarantined` false.

Offline mode: place a fixture state at `evals/fixtures/<id>.json` when LLM is unavailable.
