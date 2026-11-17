## ADDED Requirements

### Requirement: Migration creates planner_runs and downgrades only that table
The next Alembic revision after `a1b2c3d4e5f6` MUST create `planner_runs` and MUST NOT alter or drop existing application tables. Its downgrade MUST drop `planner_runs` and the run-status enum type, and MUST leave `users`, `destinations`, `places`, `trips`, `trip_places`, `trip_evaluations`, and `trip_edit_events` in place.

#### Scenario: Upgrade from the current head
- **WHEN** `alembic upgrade head` runs on a database whose current revision is `a1b2c3d4e5f6`
- **THEN** `planner_runs` exists and the seven existing application tables are unchanged

#### Scenario: Downgrade one revision
- **WHEN** `alembic downgrade -1` runs after that upgrade
- **THEN** `planner_runs` is gone and the seven existing application tables remain

#### Scenario: Upgrade again after downgrade
- **WHEN** `alembic upgrade head` runs after that downgrade
- **THEN** `planner_runs` exists again

#### Scenario: Empty database reaches the new head
- **WHEN** `alembic upgrade head` runs against an empty database
- **THEN** the upgrade completes and `planner_runs` exists along with the earlier application tables

### Requirement: Planner run model is registered for autogenerate
`migrations/env.py` MUST import the planner run model so autogenerate sees `planner_runs` on `Base.metadata`.

#### Scenario: Env load registers the table
- **WHEN** `migrations/env.py` is loaded
- **THEN** `planner_runs` is present in `Base.metadata`
