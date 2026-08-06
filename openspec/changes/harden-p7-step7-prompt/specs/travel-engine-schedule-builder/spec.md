## ADDED Requirements

### Requirement: Preserve-order schedule path for P7 reorder

The project SHALL provide a preserve-order scheduling entry point in `src/travel_engine/schedule_builder.py` — either `build_day_schedule_preserve_order(ordered_stops, route_legs)` or `build_day_schedule(..., *, preserve_order: bool = False)` — that assigns naive `"HH:MM"` times **without** running `_extract_morning_first` / morning-only omission. Default/`preserve_order=False` behavior MUST remain the existing morning-extract algorithm for generation and non-reorder edit paths. The preserve-order path MUST remain pure (no I/O) and MUST still enforce lunch-gap and duration rules. P7 REORDER MUST use the preserve-order path so persisted `order_in_day` matches the client permutation.

#### Scenario: Preserve-order keeps client sequence including late morning-only

- **WHEN** `build_day_schedule` preserve-order is called with a morning-only place in slot 3 and compatible legs
- **THEN** that place remains in slot 3 in the returned schedule (not moved to the front, not omitted)

#### Scenario: Default path still extracts morning-only

- **WHEN** `build_day_schedule` is called with default (non-preserve) behavior and a viewpoint among later stops
- **THEN** morning-extract behavior still places retained morning-only stops in order 1–2 as today
