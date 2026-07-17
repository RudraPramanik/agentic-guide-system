## Context

Step 1.3 complete: async Alembic env, migration 001 (PostGIS extensions), `geoalchemy2` registered. All five `models.py` files are one-line stubs. `Base` + mixins implemented in 1.1. Next context checkpoint: 1.4a.

Step 1.4 was intentionally split (1.4a–1.4d) so each model group is validated before autogenerate runs — a sound approach given PostGIS geometry, JSONB defaults, and composite indexes.

## Goals / Non-Goals

**Goals:**
- Implement six models exactly per `docs/steps/step1.md` §1.4a–1.4c (with known doc fixes)
- Run step validation snippets after each sub-step
- Safely autogenerate and apply migration 002
- Update `docs/context.md` after 1.4d

**Non-Goals:**
- TripEditEvent, BaseRepository, auth JWT, endpoints
- `relationship()` definitions (deferred until both sides exist)

## Decisions

### 1. Follow 1.4b for Trip SoftDeleteMixin

**Choice:** `Trip` uses `SoftDeleteMixin` as specified in 1.4b.

**Rationale:** Supports user trip deletion via repository soft-delete (1.5). Step 1.1 mixin list incorrectly excludes Trip — treat 1.4b as authoritative.

### 2. Fix missing Text import in 1.4b

**Choice:** Add `Text` to `sqlalchemy` imports in `src/trips/models.py`.

**Rationale:** `TripPlace.polyline` uses `Text`; step snippet omits import.

### 3. Add alembic/script.py.mako before 1.4d

**Choice:** Copy standard Alembic Mako template into `alembic/script.py.mako`.

**Rationale:** Verified — `alembic revision --autogenerate` fails without it.

### 4. include_object filter for PostGIS DB

**Choice:** Add to both offline and online `context.configure()` in `env.py`:

```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and compare_to is None:
        return False  # never autogenerate DROP for tables outside metadata
    return True
```

**Rationale:** PostGIS image ships Tiger geocoder tables in `public`. Without filter, autogenerate proposes dropping 40+ system tables.

### 5. JSONB / list defaults — callable only

**Choice:** `default=dict`, `default=list` on all JSONB columns per step rules.

**Rationale:** Prevents mutable shared defaults across ORM instances.

### 6. Implement in sub-step order with env.py incremental imports

**Choice:** 1.4a → validate → 1.4b → validate → 1.4c → validate → prep mako/filter → 1.4d.

**Rationale:** Matches step doc intent; catches schema mistakes before migration.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Geometry autogenerates as VARCHAR | `geoalchemy2` import in env.py (1.3); review migration before upgrade |
| Autogenerate drops PostGIS tables | `include_object` filter (new) |
| `.env` DATABASE_URL with inline comment | Fix `.env` or export bare URL for alembic CLI |
| Local `alembic/` shadows pip package | Do not set `PYTHONPATH` when running alembic CLI |
| `alembic.ini` UTF-8 BOM on Windows | Write without BOM if re-editing ini |
| Large 1.4 in one session | Keep split; one OpenSpec change, four task groups |

## Migration Plan

1. Implement models 1.4a–1.4c with env.py imports after each group
2. Run each sub-step `python -c` validation
3. Add `script.py.mako` + `include_object` to env.py
4. Autogenerate migration 002; review against 1.4d checklist
5. `alembic upgrade head`
6. psql: `\dt`, `\di`, `trip_status` type, `alembic current`
7. Update `docs/context.md` → next step 1.5

## Open Questions

- None blocking — proceed with 1.4a. TripEditEvent deliberately deferred to 1.9.
