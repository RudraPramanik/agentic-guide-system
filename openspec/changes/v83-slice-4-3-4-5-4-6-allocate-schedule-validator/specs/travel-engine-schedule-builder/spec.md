## ADDED Requirements

### Requirement: Schedule V2 uses real legs, one buffer, and a day end
`build_day_schedule` MUST accept an injected V2 mode that defaults off. The module MUST NOT call `get_settings()` and MUST NOT contain the setting names. With the mode off or omitted, timed stops MUST match the current builder, including `preserve_order=True`. With V2 mode on and `preserve_order=False`, each hop MUST advance by that hop's `RouteLeg.duration_min` plus `MIN_TRAVEL_BUFFER_MIN`. The builder MUST NOT replace a leg duration with a fixed spacing constant. It MUST insert one lunch gap using the existing lunch constants. Morning-only stops MUST remain at most two and in order 1–2. A visit that would end after `DAY_END_TIME` MUST be omitted from the timed list. Start times MUST be strictly increasing. Times MUST stay naive `"HH:MM"` with no timezone.

#### Scenario: Flag-off timing is unchanged
- **WHEN** `build_day_schedule` is called without V2 mode
- **THEN** the timed stops match the current builder for the same stops and legs

#### Scenario: V2 hop uses the leg duration plus the buffer
- **WHEN** V2 mode is on and a consecutive leg has `duration_min` of 20
- **THEN** the clock advances by 20 plus `MIN_TRAVEL_BUFFER_MIN` for that hop, not by a fixed spacing constant alone

#### Scenario: A visit past day end is omitted
- **WHEN** V2 mode is on and the next visit would end after `DAY_END_TIME`
- **THEN** that stop is absent from the returned schedule and every returned start is strictly later than the previous start

### Requirement: Verified hours are the only hours that move a stop
With V2 mode on, a stop whose opening status is `verified` and that carries a naive open and close MUST start inside that window. If arrival is before open, the builder MUST wait until open only when the visit still ends by close and by `DAY_END_TIME`; otherwise it MUST omit the stop. Status `unknown`, `malformed`, or absent MUST NOT move the stop and MUST NOT produce an arrival note that claims the place is open. `preserve_order=True` MUST keep the current preserve-order algorithm and MUST ignore V2 omission and hour waits.

#### Scenario: Unknown hours do not delay the stop
- **WHEN** V2 mode is on and a stop's opening status is `unknown`
- **THEN** its start is the arrival clock and its arrival note does not claim the place is open

#### Scenario: Verified window can delay the start
- **WHEN** V2 mode is on, arrival is before a verified open, and the visit still ends by close and by `DAY_END_TIME`
- **THEN** the stop starts at the verified open time

#### Scenario: Preserve-order ignores V2 hour shifts
- **WHEN** `preserve_order=True` and V2 mode is also requested
- **THEN** the returned order matches the input order and a late morning-only stop is not dropped for hours or day end
