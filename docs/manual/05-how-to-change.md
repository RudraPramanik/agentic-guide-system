# 05 — How to change (recipes)

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [04-imports](04-imports-and-wiring.md)

Each recipe lists **first files to open**. Follow [`AGENT.md`](../../AGENT.md). Prefer an OpenSpec change (`/opsx:propose`) for non-trivial work — see [`docs/spec.md`](../spec.md).

---

## I want a new environment variable

1. Add field + default on `Settings` in `src/config.py`  
2. Document in `.env.example`  
3. Read only via `get_settings()` — **never** `os.environ.get()` in feature code  
4. Restart / clear `get_settings` cache in long-lived processes if testing overrides  

---

## I want a new HTTP endpoint

Assume domain package already has (or you create) router → service → repository:

1. **Schema** — Pydantic in `src/<domain>/schemas.py`  
2. **Repository** — extend `BaseRepository` in `src/<domain>/repository.py` (DB only)  
3. **Service** — orchestration in `src/<domain>/service.py`  
4. **Router** — FastAPI routes; depend on service + `get_db` / auth deps  
5. Return `ApiResponse[T]` or `PaginatedResponse[T]` — no raw dicts  
6. Register router in `src/main.py` (`include_router`)  
7. Update `docs/context.md` Live endpoints when validated  

**Wrong:** SQL in the router, or calling Nominatim from the service without going through `src/geo/`.

---

## I want to call Nominatim or Overpass

1. Open `src/geo/geocoder.py` or `src/geo/overpass.py`  
2. Call `geocode()` / `fetch_pois()` from a **service or script**  
3. Handle `None` / `[]` fallbacks — never assume success  
4. Do **not** construct OverpassQL or Nominatim URLs elsewhere  
5. Validate with `scripts/test_geocoder.py` / `scripts/test_overpass.py`  
6. If public Overpass is down, override `OVERPASS_API_URL` (see context.md)  

OSRM: wait for step 2.5 — `geo/osrm.py` is still a stub.

---

## I want to seed a destination (or write another batch script)

1. Run it: `python scripts/seed_destination.py --destination "Darjeeling" --radius 30` (idempotent)  
2. Read `scripts/seed_destination.py` as the batch template: geo gateway → repositories → single commit at the end  
3. Wrap each item in `async with session.begin_nested()` so one bad row rolls back to its savepoint instead of aborting the whole transaction  
4. Log skips (`log.warning("seed.poi_failed", ...)`) and keep going — only a fatal precondition (geocode miss) exits non-zero  
5. Keep the per-item loop in a plain importable function so tests can drive it without the CLI  
6. Scripts commit; repositories only flush  

**Wrong:** calling httpx/Overpass directly from a script, or letting one failed row abort the batch.

---

## I want a new database table / column

1. Edit or add SQLAlchemy model under the right package (`models.py`) using mixins from `core/database/base.py`  
2. Ensure `alembic/env.py` imports the model  
3. `alembic revision --autogenerate -m "..."` then review the migration  
4. `alembic upgrade head` (not at app startup)  
5. Add repository methods as needed; keep writes flush-only unless a service intentionally commits  

---

## I want to require login on a route

1. Use `Depends(require_auth)` from `src/core/security/permissions.py`  
2. For optional guest+user: `optional_auth` (see auth `/me`)  
3. Tokens: Bearer header or `wandr_token` cookie — don’t invent a third scheme without design  

---

## I want to call an LLM

1. Only `from src.core.llm.client import chat_completion` (or `chat_with_tools`)  
2. Never import `litellm` / vendor SDKs elsewhere  
3. Don’t ask the model for place IDs, lat/lng, or schedule times  

---

## I want to run validation / tests

```bash
docker compose up -d
# set PYTHONPATH to repo root if needed
python scripts/test_db_conn.py
python scripts/test_p1_smoke.py
python scripts/test_geocoder.py "Darjeeling"
python scripts/test_overpass.py 27.041 88.263 30
python scripts/seed_destination.py --destination "Darjeeling" --radius 30
python -m pytest tests/ -v
uvicorn src.main:app --reload
```

DB URL uses port **5433** locally — see `docs/context.md`.

---

## I want to know if something is already built

1. Check **Implemented modules** and **Stubs only** in `docs/context.md`  
2. If stub (~1 line), don’t design callers against imaginary APIs  
3. For behavior contracts of shipped slices, see `openspec/specs/`  

Next: [06 — Maintenance](06-maintenance.md)
