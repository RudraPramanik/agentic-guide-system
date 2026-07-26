## Purpose

Place read layer — `PlaceOut` schema (geometry-derived coordinates) and `PlaceService` with a mandatory destination-existence check before listing. Router → Service → Repository only; service uses `DestinationRepository` solely for the existence guard.

## Requirements

### Requirement: PlaceOut schema with geometry-derived coordinates

The system SHALL expose `PlaceOut` (Pydantic) for place read models with `id`, `osm_id`, `name`, `category`, `tags`, `summary`, `lat`, `lng`, `destination_id`, and `created_at`. `lat`/`lng` MUST be derived at serialization time from `Place.location` via `geoalchemy2.shape.to_shape` (`.y` = lat, `.x` = lng), not stored as separate ORM columns. A `from_place(place: Place) -> PlaceOut` classmethod SHALL perform that mapping.

#### Scenario: from_place populates lat/lng from geometry

- **WHEN** `PlaceOut.from_place` is called on a persisted Place with a valid Point location
- **THEN** `lat` and `lng` are non-zero floats matching the geometry coordinates

### Requirement: PlaceService list and get with mandatory destination check

The system SHALL provide `PlaceService` constructed with an `AsyncSession`, using `PlaceRepository` for place reads and `DestinationRepository` only for destination existence. `list_by_destination(destination_id, params)` MUST: (1) verify the destination exists and raise `DestinationNotFoundError` if not; (2) then call `PlaceRepository.list_by_destination`; (3) return `[PlaceOut.from_place(...)]` and total. It MUST NOT return `total=0` for a nonexistent destination. `get_by_id(place_id)` MUST use place `get_by_id_or_raise` and return `PlaceOut.from_place`.

#### Scenario: List seeded destination returns places

- **WHEN** Darjeeling (or another seeded destination) exists with places and `list_by_destination` is called with `PageParams(page=1, size=5)`
- **THEN** `total >= 1` and the first item has non-zero `lat`

#### Scenario: Garbage destination_id raises DestinationNotFoundError

- **WHEN** `list_by_destination` is called with a random UUID that is not a destination
- **THEN** `DestinationNotFoundError` is raised (404 semantics) and no empty page is returned

#### Scenario: get_by_id returns PlaceOut

- **WHEN** `get_by_id` is called with an existing place id
- **THEN** a `PlaceOut` is returned with matching id and geometry-derived coordinates
