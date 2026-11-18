## MODIFIED Requirements

### Requirement: save_from_state persists base coordinates in preferences

When `state` contains both `base_lat` and `base_lng` values that successfully coerce to `float`, `TripService.save_from_state` MUST store them on `Trip.preferences` as floats alongside existing keys (`interests`, `budget`, `include_offbeat`, `include_trekking`). When either value is missing or not coercible, preferences MUST omit both `base_lat` and `base_lng` (save MUST still succeed). `base_lat` and `base_lng` MUST NOT be copied from `discovery_anchor`. `TripService` MUST NOT call `PlannerService`.

`Trip` MUST also have nullable JSON columns `discovery_anchor` and `search_area`. When state has no search area, both columns MUST be null. When state has a server-built anchor and search area, the save MUST store those two objects and MUST NOT put them inside `preferences`.

#### Scenario: Save stores base prefs when present

- **WHEN** `save_from_state` runs with a usable schedule and numeric `base_lat` / `base_lng` on state
- **THEN** the committed trip’s `preferences` include those float values

#### Scenario: Save omits base keys when absent

- **WHEN** `save_from_state` runs without `base_lat` / `base_lng` on state
- **THEN** the trip is saved and `preferences` do not contain `base_lat` or `base_lng`

#### Scenario: Flag-off save leaves the new columns null

- **WHEN** `save_from_state` runs with a usable schedule and no search area on state
- **THEN** `discovery_anchor` and `search_area` are null and `preferences` still hold the trip base when it was present

#### Scenario: Flag-on save stores the area outside preferences

- **WHEN** `save_from_state` runs with a search area and a discovery anchor on state, and a different numeric trip base
- **THEN** the two columns hold those objects and `preferences.base_lat` / `preferences.base_lng` remain the trip base

## ADDED Requirements

### Requirement: Trip JSON omits a null anchor and search area
`TripOut` MUST include `discovery_anchor` and `search_area` only when the stored value is non-null. A trip saved with both columns null MUST serialize without those keys. `_resolve_base` MUST keep reading `preferences` and then the destination center. It MUST NOT read `discovery_anchor`.

#### Scenario: A legacy trip payload does not grow
- **WHEN** a client fetches a trip whose anchor and search area are null
- **THEN** the JSON object has no `discovery_anchor` key and no `search_area` key

#### Scenario: A located trip returns both objects
- **WHEN** a client fetches a trip whose columns are set
- **THEN** the JSON includes `discovery_anchor` and `search_area` and the trip base remains under `preferences`

#### Scenario: Route start ignores the anchor
- **WHEN** `_resolve_base` runs for a trip whose anchor coordinates differ from `preferences.base_lat` and `preferences.base_lng`
- **THEN** the returned coordinates are the preference values
