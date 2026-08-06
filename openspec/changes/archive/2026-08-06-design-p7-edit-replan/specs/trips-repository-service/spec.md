## ADDED Requirements

### Requirement: Persist generation base coords on Trip preferences

`TripService.save_from_state` MUST store `base_lat` and `base_lng` from the planner `TravelState` into `Trip.preferences` (JSON keys `base_lat` / `base_lng` as floats) when present, in the same Unit of Work that creates the Trip and TripPlaces. No new DB columns or migrations are required for this persistence.

#### Scenario: Saved trip preferences include base

- **WHEN** `save_from_state` runs with state containing `base_lat` and `base_lng`
- **THEN** the committed Trip’s `preferences` include those float values under `base_lat` and `base_lng`

### Requirement: Resolve base coords for day surgery

Trip edit operations MUST resolve routing base coordinates as: use `trip.preferences["base_lat"]` and `["base_lng"]` when both are present and numeric; otherwise use the trip’s `Destination.lat` / `Destination.lng`. Edits MUST NOT require the client to send base coordinates.

#### Scenario: Prefs base preferred over destination

- **WHEN** preferences contain base_lat/base_lng and destination coords differ
- **THEN** day surgery / optimize uses the preferences base

#### Scenario: Legacy trip falls back to destination

- **WHEN** preferences lack base_lat/base_lng
- **THEN** day surgery uses the destination’s lat/lng
