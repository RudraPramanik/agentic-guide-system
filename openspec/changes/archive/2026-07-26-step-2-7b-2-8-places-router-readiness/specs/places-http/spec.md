## ADDED Requirements

### Requirement: Places list and get HTTP endpoints

The system SHALL expose an `APIRouter` with prefix `/api/v1/places` and tags `["places"]`. `GET /api/v1/places` MUST accept required query `destination_id` (`uuid.UUID`) and `PageParams`, call `PlaceService.list_by_destination` only, and return `PaginatedResponse[PlaceOut]` via `paginate`. `GET /api/v1/places/{place_id}` MUST call `PlaceService.get_by_id` only and return `ApiResponse[PlaceOut]`. The router MUST NOT import repositories, touch the session beyond `Depends(get_db)`, or return raw ORM models.

#### Scenario: Paginated list for seeded destination

- **WHEN** a seeded destination has ≥50 places and a client requests `/api/v1/places?destination_id={DESTINATION_ID}&page=2&size=10`
- **THEN** the response is 200 with `total >= 50`, `page=2`, `pages>=5`, `has_next=true`, and `items` length 10

#### Scenario: Get place by id

- **WHEN** a client requests `/api/v1/places/{PLACE_ID}` for an existing place
- **THEN** the response is 200 `ApiResponse` whose `data` is a `PlaceOut` with matching id and non-zero lat/lng

#### Scenario: Unknown place returns 404

- **WHEN** a client requests `/api/v1/places/00000000-0000-0000-0000-000000000001`
- **THEN** the response is 404

#### Scenario: Unknown destination on list returns 404 not empty page

- **WHEN** a client requests `/api/v1/places?destination_id=00000000-0000-0000-0000-000000000001&page=1`
- **THEN** the response is 404 with code `not_found` and MUST NOT be 200 with an empty `items` array

### Requirement: Places router registration

The system SHALL register the places router in `src/main.py` via `app.include_router` so both places routes are reachable when the app starts.

#### Scenario: Places routes mounted on the app

- **WHEN** the FastAPI app starts
- **THEN** `/api/v1/places` is reachable (not 404 from a missing route registration)
