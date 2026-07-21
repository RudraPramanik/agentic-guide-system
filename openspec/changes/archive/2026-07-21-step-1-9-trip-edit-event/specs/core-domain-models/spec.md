## ADDED Requirements

### Requirement: Trips domain includes TripEditEvent audit model

The trips domain models module SHALL export `EditType` and `TripEditEvent` in addition to `TripStatus`, `Trip`, and `TripPlace`.

#### Scenario: Import trip edit types

- **WHEN** code executes `from src.trips.models import TripEditEvent, EditType`
- **THEN** import succeeds without error

#### Scenario: TripEditEvent repr is debug-friendly

- **WHEN** `repr(TripEditEvent(...))` is called
- **THEN** output includes id, trip_id, and edit_type
