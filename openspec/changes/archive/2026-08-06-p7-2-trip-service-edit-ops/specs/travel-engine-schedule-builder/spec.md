## MODIFIED Requirements

### Requirement: Preserve-order schedule path for P7 reorder

The project SHALL provide a preserve-order scheduling entry point in `src/travel_engine/schedule_builder.py` via `build_day_schedule(ordered_stops, route_legs, *, preserve_order: bool = False)` (and MAY expose a thin `build_day_schedule_preserve_order` alias). When `preserve_order=True`, the function MUST assign naive `"HH:MM"` times **without** running `_extract_morning_first` / morning-only omission — the returned stop sequence MUST match `ordered_stops` order exactly. Default/`preserve_order=False` behavior MUST remain the existing morning-extract algorithm for generation and non-reorder edit paths. The preserve-order path MUST remain pure (no I/O) and MUST still enforce lunch-gap, duration, and consecutive-leg lookup rules. P7 REORDER MUST call the preserve-order path so persisted `order_in_day` matches the client permutation.

#### Scenario: Preserve-order keeps client sequence including late morning-only

- **WHEN** `build_day_schedule` is called with `preserve_order=True`, a morning-only place in slot 3, and compatible legs
- **THEN** that place remains in slot 3 in the returned schedule (not moved to the front, not omitted)

#### Scenario: Default path still extracts morning-only

- **WHEN** `build_day_schedule` is called with default (non-preserve) behavior and a viewpoint among later stops
- **THEN** morning-extract behavior still places retained morning-only stops in order 1–2 as today

#### Scenario: Preserve-order still inserts lunch gap

- **WHEN** preserve-order scheduling would place the next visit such that it crosses `LUNCH_BREAK_START`
- **THEN** a lunch gap of `LUNCH_BREAK_MIN` is inserted before that visit
