## Purpose

Turns an OSM opening-hours string into a verified window, an unknown value, or a malformed value, without claiming a place is open now.

## Requirements

### Requirement: Hours parse to verified, unknown, or malformed

The system SHALL parse an OSM opening-hours string with an in-repo grammar and no new package. The original string MUST be kept on the result whenever the input was non-empty. The result MUST be one of `verified`, `unknown`, or `malformed`.

A null, empty, or whitespace-only input MUST be `unknown`, with a null raw value and null open and close times.

The only `verified` open windows MUST be the exact grammar `24/7` and `Mo-Su HH:MM-HH:MM`. `24/7` MUST set open `00:00` and close `24:00`. The clock form MUST set those hours and minutes. Hours MUST be 00 through 23 except that close MAY be `24:00`. Minutes MUST be 00 through 59. Close MUST be later than open. The whole trimmed string MUST match. A second rule, a comma, or a semicolon MUST NOT be verified.

`off` and `closed`, case-insensitive and as the whole trimmed string, MUST be `verified` with open `00:00` and close `00:00`. That empty window means closed all week. It MUST NOT be treated as an open interval.

A non-empty string that states a weekday other than all-week `Mo-Su`, a month, a public holiday, sunrise, sunset, dawn, or dusk MUST be `unknown` with null open and close times and the raw string kept. Any other non-empty string MUST be `malformed` with null open and close times and the raw string kept.

The parser MUST NOT return a status of open-now, MUST NOT read the clock, and MUST NOT read a timezone.

#### Scenario: Absent hours are unknown

- **WHEN** the input is null or whitespace
- **THEN** the status is `unknown`, the raw value is null, and both times are null

#### Scenario: All-week window is verified

- **WHEN** the input is `Mo-Su 09:00-17:00`
- **THEN** the status is `verified`, the raw string is preserved, open is `09:00`, and close is `17:00`

#### Scenario: Always open is a full-day window

- **WHEN** the input is `24/7`
- **THEN** the status is `verified`, open is `00:00`, and close is `24:00`

#### Scenario: Closed all week is an empty verified window

- **WHEN** the input is `off`
- **THEN** the status is `verified`, open is `00:00`, and close is `00:00`

#### Scenario: Weekday-only hours stay unknown

- **WHEN** the input is `Mo-Fr 09:00-17:00`
- **THEN** the status is `unknown`, the raw string is preserved, and both times are null

#### Scenario: Unrecognized text is malformed

- **WHEN** the input is `every morning`
- **THEN** the status is `malformed`, the raw string is preserved, and both times are null

### Requirement: Flag-on mapping feeds the engine and flag-off leaves hours unknown

When `READINESS_V2_ENABLED` is true, every conversion of a stored place into a `PlaceCandidate` used by planner search and by trip-edit rebuilds MUST apply this parser to the string in the place's `opening_hours` tag. The candidate MUST carry the status, the open and close strings, and the raw string. When the tag is absent, the candidate MUST be `unknown` with null times.

When the flag is false, those conversions MUST leave `opening_hours_status` at `unknown`, and open, close, and raw hours null, even if the tag is present.

The travel engine MUST NOT parse the raw string. A candidate whose status is `unknown` or `malformed` MUST NOT produce a schedule note that says the place is open, and MUST NOT raise `OPENING_HOURS_CONFLICT`. A `verified` window that cannot contain the visit MUST be omitted from the V2 schedule. A `verified` empty window (`00:00` to `00:00`) MUST NOT be placed as an open visit. Only a `verified` window with a real interval MAY raise `OPENING_HOURS_CONFLICT`, and only when a stop still falls outside that interval.

#### Scenario: Flag off ignores a present tag

- **WHEN** the flag is false and the place tag is `Mo-Su 09:00-17:00`
- **THEN** the candidate status is `unknown` and both times are null

#### Scenario: Flag on copies a verified window

- **WHEN** the flag is true and the place tag is `Mo-Su 09:00-17:00`
- **THEN** the candidate status is `verified`, open is `09:00`, and close is `17:00`

#### Scenario: Malformed hours are not an open visit

- **WHEN** a candidate has status `malformed` and a V2 schedule is built
- **THEN** no stop note says the place is open, and the findings do not include `OPENING_HOURS_CONFLICT` for that place

#### Scenario: Unknown hours are not an open visit

- **WHEN** a candidate has status `unknown` and a V2 schedule is built
- **THEN** no stop note says the place is open, and the findings for that place are `OPENING_HOURS_UNKNOWN` rather than `OPENING_HOURS_CONFLICT`
