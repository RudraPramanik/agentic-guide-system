## ADDED Requirements

### Requirement: Trips gain nullable anchor and search-area columns
An Alembic revision MUST add nullable JSONB columns `trips.discovery_anchor` and `trips.search_area`. It MUST NOT backfill existing rows, MUST NOT drop or retype any existing column, and MUST NOT change `preferences`. Downgrade MUST drop only those two columns. Upgrade then downgrade then upgrade MUST leave an existing trip's other columns intact, with the two new columns null after the second upgrade.

#### Scenario: Upgrade adds the columns on an empty database
- **WHEN** `alembic upgrade head` runs on an empty database
- **THEN** `trips` has nullable `discovery_anchor` and `search_area` columns

#### Scenario: Downgrade removes only the new columns
- **WHEN** `alembic downgrade -1` runs after that upgrade
- **THEN** those two columns are gone and the rest of `trips` remains

#### Scenario: Existing rows are not rewritten
- **WHEN** upgrade runs against a database that already has trips
- **THEN** those rows keep their previous columns and the new columns are null
