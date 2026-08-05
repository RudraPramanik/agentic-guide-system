## ADDED Requirements

### Requirement: TravelState.schedule uses locked day-dict shape
`TravelState.schedule` MUST be documented (module comment and/or adjacent contract note in `src/planner/graph/state.py`) as a list of per-day dicts with this shape (step 6.0 / `docs/steps/step6.md`):

```
{
  "day": int,
  "stops": [
    {
      "place_id": str, "name": str, "lat": float, "lng": float, "category": str,
      "order": int, "travel_time_min": int, "visit_duration_min": int,
      "suggested_start_time": str, "arrival_note": str | None,
      "leg_polyline": str | None
    },
    ...
  ],
  "total_distance_km": float,
  "total_travel_min": int,
  "day_polyline": str | None
}
```

TypedDict may keep `schedule: list[Any]` for LangGraph flexibility, but producers (`build_schedule`) and adapters (`validate_itinerary`, narrative helpers) MUST treat the day-dict shape as the runtime contract. The prior `list[list[stop]]` shape is retired.

#### Scenario: Contract documents day dict keys
- **WHEN** an implementer reads `TravelState` documentation in `state.py`
- **THEN** the day-dict schedule shape including `leg_polyline` / `day_polyline` is stated explicitly

#### Scenario: No I/O resources on TravelState (unchanged)
- **WHEN** type hints for `TravelState` are inspected
- **THEN** `"db"` and `"routing"` remain absent from the hint keys
