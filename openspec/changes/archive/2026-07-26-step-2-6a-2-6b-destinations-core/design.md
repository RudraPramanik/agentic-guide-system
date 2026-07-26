## Context

P2.3 delivered `PlaceRepository` (atomic OSM upsert). Next per `docs/context.md` and canonical order in `docs/steps/step2.md`:

```
2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → …
```

`Destination` model + migration 002 already exist. `src/destinations/{schemas,exceptions,repository,service,router}.py` are still step-0.1 stubs. Geocoder (`geo.geocode` → `GeocodedPlace | None`) is live.

**Verdict on step2.md §2.6a+2.6b:** **Good to implement as written.** No blueprint rewrite required. Small implementation clarifications below (not step-doc blockers).

## Goals / Non-Goals

**Goals:**

- Ship 2.6a schemas/exceptions and 2.6b repository/service so 2.4 seed and 2.6c router can proceed
- Preserve v2 atomic upsert (no IntegrityError race) and clear failure boundaries
- Confirm env/Alembic prerequisites so validation runs smoothly

**Non-Goals:**

- HTTP router, rate-limit path rule, seed CLI, OSRM, places service, readiness scoring, pytest module
- Changing `alembic/env.py` or adding migrations
- New config/env keys

## Decisions

### D1 — Follow step2.md as-is (no step rewrite)

| Area | Step text | Project fit |
|------|-----------|-------------|
| Order 2.6a→2.6b before 2.4 | Locked | Correct — seed needs `upsert_from_geocoded` |
| Atomic `ON CONFLICT (osm_place_id)` | Matches PlaceRepo pattern | Aligns with existing `places/repository.py` |
| Counters excluded from SET | Locked design decision | Model has `place_count`/`enriched_count`/`indexed_count` owned by seed/enrich |
| Cache-aside search | DB → geocode → upsert → commit | Matches AuthService commit-on-standalone-write |
| Geocode miss → 404 | `DestinationNotFoundError` | Correct — not 502 (`geocode` already falls back to `None`) |
| Schemas without model imports | Explicit | Matches auth schemas pattern |

**Alternatives rejected:** Skipping to 2.4 first (breaks on missing repo); check-then-insert upsert (v1 race); raising 502 on geocode miss (misclassifies “unknown place”).

### D2 — `get_by_id` wraps to `DestinationNotFoundError`

`BaseRepository.get_by_id_or_raise` raises generic `NotFoundError`. Step says service raises `DestinationNotFoundError`.

**Implement:** `get_by_id` uses `repo.get_by_id`; if `None`, raise `DestinationNotFoundError(destination_id=str(id))`. Do not leak generic `NotFoundError` from this service method.

### D3 — `search_by_name` fill-in (docstring-only in step)

```text
strip query → ILIKE %q% on name OR display_name
ORDER BY place_count DESC, name ASC
LIMIT (default 10)
```

`Destination` has **no** `SoftDeleteMixin` — no `deleted_at` filter needed (optional: still call `_soft_delete_filter()` for consistency; it returns `true()`).

### D4 — Env vars for smooth 2.6a/2.6b validation

| Variable | Needed now? | Notes |
|----------|-------------|-------|
| `DATABASE_URL` | **Yes** | Postgres `:5433` — already in `.env` |
| `NOMINATIM_USER_AGENT` | **Yes** | Must be a **real** contact email; placeholder `yourname@email.com` risks Nominatim blocks |
| `NOMINATIM_BASE_URL` | Optional | Default in `config.py` is fine |
| `OVERPASS_API_URL` | **No** (until 2.4) | Defaults exist; unused by 2.6a/b |
| `OSRM_BASE_URL` | **No** (until 2.5) | Already in `.env`; unused here |
| LLM / Google / Langfuse / Redis | **No** | Not on this path |

**No new Settings fields** for 2.6a/2.6b.

### D5 — Do **not** put API env in `alembic/env.py`

`alembic/env.py` already:

- Loads `DATABASE_URL` via `get_settings()`
- Imports `Destination` (and all other models) for autogenerate metadata

For 2.6a/2.6b: **zero Alembic edits, zero new migrations.** Tables already exist. Nominatim/Overpass/OSRM keys belong only in `.env` + `src/config.py` (`get_settings()`), never in Alembic.

### D6 — Failure boundaries (locked)

| Layer | Failure | Behavior |
|-------|---------|----------|
| `geo.geocode` | HTTP/timeout after retry | Returns `None` (existing gateway) |
| `DestinationService.search` | `geocode` → `None` | `DestinationNotFoundError` (404 at API later) |
| `DestinationRepository.upsert_from_geocoded` | Concurrent same `osm_place_id` | Both succeed via `ON CONFLICT`; same row |
| Repository | — | Never calls Nominatim; flush only |
| Service miss path | After upsert | `session.commit()` + `refresh` (AuthService pattern) |
| Service hit path | DB rows found | Return; no geocode, no commit |

Must **not:** return 502 for geocode miss; check-then-insert; import httpx in destinations; commit inside repository.

### D7 — Validation practicalities

- Step scripts use `AsyncSessionLocal` — exists in `session.py` as a callable factory; `async with AsyncSessionLocal() as session:` works
- Run from project root with env loaded (same as other scripts); set `PYTHONPATH=.` on Windows if needed
- Happy-path search needs live Nominatim + DB; atomic-upsert failure script needs DB only (no network)
- Race script is sequential double-upsert (proves idempotent SQL); true multi-session concurrency is optional hardening, not required by step

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Nominatim blocks generic/placeholder User-Agent | Set real email in `.env` before 2.6b search validation |
| Public Nominatim rate limits / flakiness | Geocoder already throttles 1 req/sec + caches; re-run validation; DB-hit path skips network |
| Implementer forgets counter exclusion on ON CONFLICT SET | Spec + PlaceRepo mirror; code review checklist |
| Confusing Alembic with API config | Explicit non-goal: leave `alembic/env.py` alone |
| Router still stub → no HTTP proof yet | Acceptable; service-level scripts are the step gate; 2.6c wires API |

## Migration Plan

1. Implement 2.6a → import/assert validation
2. Implement 2.6b → search + atomic upsert validations
3. Update `docs/context.md` (2.6a+2.6b ✅, Next → **2.4**)
4. Rollback: revert the four destination modules to stubs (no DB schema to roll back)

## Open Questions

*None blocking.* Optional later: true concurrent upsert test with two sessions (nice-to-have for 2.9, not required now).
