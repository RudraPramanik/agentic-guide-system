## MODIFIED Requirements

### Requirement: No ORM relationships in step 1.4 models
Models from step 1.4 originally MUST NOT define `relationship()` until both sides exist. As of step **6.1**, `Trip`, `TripPlace`, and `Place` MAY define SQLAlchemy `relationship()` mappings solely to support eager loading in `TripRepository.get_with_places` (and later GeoJSON/schema mapping). Relationships MUST NOT introduce new columns or require an Alembic migration. Other domain models MAY remain relationship-free until a later step needs them.

#### Scenario: Trip eager-load relationships exist for 6.1
- **WHEN** `Trip` / `TripPlace` models are inspected after step 6.1
- **THEN** relationships exist so `get_with_places` can selectinload places and Place without N+1 queries

#### Scenario: No schema migration for relationships
- **WHEN** relationships are added for Trip/TripPlace/Place
- **THEN** no new table columns are introduced and no Alembic revision is required for this change
