## Context

Models and migration 002 exist. `base_repository.py` is a one-line stub. Step 1.5 encodes Generic Repository + Specification (equality filters as data) + Unit of Work (flush, no commit).

## Goals / Non-Goals

**Goals:** Implement complete `BaseRepository` per step 1.5; pass model_class + soft-delete validation.

**Non-Goals:** Domain repos, commits in repository, raw SQL filters.

## Decisions

### 1. Follow step 1.5 method bodies exactly

**Choice:** Implement as specified in `docs/steps/step1.md` §1.5.

**Rationale:** Prescriptive and aligns with blueprint repository pattern.

### 2. Soft-delete via hasattr(deleted_at)

**Choice:** Filter `deleted_at.is_(None)` when attribute exists; else `true()`.

**Rationale:** Destination/TripEvaluation lack SoftDeleteMixin; User/Place/Trip have it.

### 3. Flush without commit

**Choice:** All writes call `flush` (+ `refresh` for create/update); never `commit`.

**Rationale:** Unit of Work — service owns transaction boundary.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| model_class resolution fails on odd inheritance | Validation with UserRepo/DestRepo subclasses |
| timezone-aware `deleted_at` vs naive column | Follow step (`datetime.now(timezone.utc)`); DB accepts |

## Open Questions

- None
