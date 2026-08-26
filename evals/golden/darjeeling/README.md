# Golden eval cases — Darjeeling

Property-based cases only (never exact narrative strings).

Required fields per case:
- `id` — stable case id (`dar-NNN`)
- `destination` — human name
- `destination_id` — UUID (optional; runner may resolve by name)
- `raw_input` — planner prompt
- `must_include_places` — optional name list (case-insensitive)
- `assertions` — object with any of:
  - `validation_passed`, `max_days`, `min_places_per_day`
  - `readiness_score_min`, `no_geo_fallback`, `max_tool_calls`

Offline mode: place a fixture state at `evals/fixtures/<id>.json` when LLM is unavailable.
