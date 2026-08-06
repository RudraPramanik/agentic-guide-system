## ADDED Requirements

### Requirement: save_from_state persists base coordinates in preferences

When `TravelState` includes numeric `base_lat` / `base_lng`, `TripService.save_from_state` MUST store them on `Trip.preferences` alongside existing preference keys. When absent, preferences MUST omit those keys (legacy trips fall back at edit time). `TripService` MUST provide `_resolve_base(trip, destination) -> tuple[float, float]` that prefers numeric prefs base coords and otherwise uses `destination.lat` / `destination.lng`. Non-numeric prefs values MUST be treated as missing. The resolve helper MUST NOT raise HTTP 500.

#### Scenario: Save stores base prefs when present

- **WHEN** `save_from_state` runs with state containing `base_lat` and `base_lng`
- **THEN** the committed trip’s `preferences` include those floats

#### Scenario: Resolve prefers preferences over destination

- **WHEN** `_resolve_base` is called with prefs base set and a different destination centroid
- **THEN** the returned coordinates are the preferences values

#### Scenario: Resolve falls back to destination

- **WHEN** prefs lack numeric base keys
- **THEN** `_resolve_base` returns `destination.lat` / `destination.lng`

### Requirement: TripService day-edit operations surface

`TripService` SHALL expose `reorder_stops`, `remove_stop`, `add_stop`, and `reoptimize_day` (owner-checked) that perform day surgery via travel_engine + injected `RoutingProvider`, validate, persist TripPlaces + one `TripEditEvent`, call `EvaluationService.mark_trip_edited`, and commit in one UoW — per `p7-trip-edit-replan` / `docs/steps/step7.md` v2.1. Domain exceptions MUST include `TripEditValidationError` (422), `TripStopConflictError` (409), and `TripStopNotFoundError` (404 `stop_not_found_on_day`).

#### Scenario: Edit methods exist on TripService

- **WHEN** `TripService` is inspected after P7 service step
- **THEN** it defines `reorder_stops`, `remove_stop`, `add_stop`, and `reoptimize_day`
