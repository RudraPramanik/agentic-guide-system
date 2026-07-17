## Why

Steps 1.1–1.4 delivered models and tables. Domain repositories need a shared async CRUD base with soft-delete filtering and Unit of Work (flush, never commit). Step **1.5** (`docs/steps/step1.md`) implements `BaseRepository[ModelT, IDT]`.

## What Changes

- Implement `src/core/database/base_repository.py` with full methods: `get_by_id`, `get_by_id_or_raise`, `exists`, `list_paginated`, `create`, `update`, `soft_delete`
- Soft-delete aware reads; models without `deleted_at` use `true()` filter
- Writes flush only — service owns `commit()`

### Non-goals

- Concrete domain repositories (auth UserRepo comes in 1.7)
- JWT, middleware, routers

## Capabilities

### New Capabilities

- `base-repository`: Generic async repository with soft-delete and equality-filter pagination

### Modified Capabilities

- _(none)_

## Impact

| Area | Effect |
|------|--------|
| **Files** | `src/core/database/base_repository.py` stub → real |
| **Dependencies** | None |
| **APIs** | None |
| **Prerequisites** | Steps 1.1–1.4 done (User, Destination for validation) |
