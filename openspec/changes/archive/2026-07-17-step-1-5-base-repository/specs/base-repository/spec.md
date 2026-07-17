## ADDED Requirements

### Requirement: BaseRepository resolves model class from generics

`BaseRepository[ModelT, IDT]` SHALL expose `model_class` resolving `ModelT` from subclass type parameters.

#### Scenario: Subclass model resolution

- **WHEN** `UserRepo(BaseRepository[User, uuid.UUID])` and `DestRepo(BaseRepository[Destination, uuid.UUID])` are constructed
- **THEN** `model_class` is `User` and `Destination` respectively

### Requirement: Soft-delete filter is model-aware

Reads SHALL exclude soft-deleted rows when `deleted_at` exists; models without it SHALL apply no soft-delete filter.

#### Scenario: User vs Destination filters

- **WHEN** `_soft_delete_filter()` is called on User and Destination repos
- **THEN** User filter references `deleted_at`; Destination filter is SQL `true()`

### Requirement: Writes flush but do not commit

`create`, `update`, and `soft_delete` SHALL flush (and refresh where specified) and MUST NOT call `session.commit()`.

#### Scenario: Unit of Work boundary

- **WHEN** a repository write method completes
- **THEN** changes are flushed to the session but the transaction remains open for the service layer

### Requirement: Missing entities raise NotFoundError

`get_by_id_or_raise` and `update` / `soft_delete` (via get) SHALL raise `NotFoundError` from `src.core.exceptions` when the row is missing or soft-deleted.

#### Scenario: Not found

- **WHEN** `get_by_id_or_raise` is called for an unknown id
- **THEN** `NotFoundError` is raised with details containing the id
