## Context

Steps 1.1–1.2 delivered `Base` + mixins and async session/engine in `src/core/database/`. `alembic.ini` and `alembic/env.py` are one-line placeholders. Docker already runs `postgis/postgis:16-3.4` on port 5433. Domain packages remain stubs — no tables yet.

Step 1.3 (`docs/steps/step1.md`) is intentionally narrow: wire Alembic for async, bootstrap extensions, prepare autogenerate for 1.4+.

## Goals / Non-Goals

**Goals:**

- Install and pin `alembic` + `geoalchemy2`.
- Configure Alembic async env aligned with existing `get_settings().DATABASE_URL` and `Base.metadata`.
- Ship migration 001 (PostGIS + uuid-ossp).
- Validate with CLI proof commands from the step doc.

**Non-Goals:**

- Domain models, migration 002, repositories, auth, middleware.
- App startup migration hooks.
- CI/CD pipeline for migrations (future concern).

## Decisions

### 1. Async Alembic env (Alembic 1.13+ pattern)

**Choice:** Use `async_engine_from_config` + `run_sync(do_run_migrations)` + `asyncio.run()` in `run_migrations_online()`.

**Rationale:** Matches step 1.3 spec verbatim; consistent with `postgresql+asyncpg` URL already used by `session.py`. Avoids maintaining a separate sync URL.

**Alternative rejected:** Sync engine with `psycopg2` — would require a second driver and diverge from app config.

### 2. DATABASE_URL injection via get_settings()

**Choice:** `config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)` in `env.py`; omit URL from `alembic.ini`.

**Rationale:** AGENT.md — all env via `get_settings()`. Single source of truth with the app.

### 3. NullPool for migration engine

**Choice:** `poolclass=pool.NullPool` in async migration engine.

**Rationale:** Short-lived CLI process; no need for connection pooling. Standard Alembic async recipe.

### 4. Manual migration 001 (not autogenerate)

**Choice:** Hand-written `001_enable_postgis.py` with raw `op.execute()` SQL.

**Rationale:** No models exist yet; extensions are infrastructure, not ORM metadata. Autogenerate cannot emit `CREATE EXTENSION`.

### 5. Empty downgrade for extensions

**Choice:** `downgrade()` is `pass`.

**Rationale:** Step doc explicitly forbids dropping shared extensions. Safer for dev DBs that may pre-install PostGIS.

### 6. geoalchemy2 side-effect import

**Choice:** `import geoalchemy2  # noqa: F401` at top of `env.py`.

**Rationale:** Required before 1.4b Place model with `Geometry` column; prevents autogenerate emitting wrong column types (called out in step 1.4d review checklist).

### 7. alembic.ini file_template

**Choice:** `%%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s`, `timezone = UTC`, `prepend_sys_path = .`

**Rationale:** Matches step doc; sortable dated revision files for future migrations.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Postgres not running / wrong port | Proof step uses `docker compose up -d`; context.md documents port 5433 |
| `.env` comment on same line as `DATABASE_URL` | Documented in context.md; validate with `scripts/test_db_conn.py` first |
| Forgetting model imports in env.py after 1.4 | Step 1.4a explicitly updates env.py; spec requirement documents the pattern |
| `asyncio.run()` in env.py conflicts if called from running loop | Alembic CLI is sync entrypoint — not invoked from FastAPI event loop |

## Migration Plan

1. `pip install alembic==1.18.4 geoalchemy2==0.20.0`
2. Replace `alembic.ini`, `alembic/env.py`
3. Add `alembic/versions/001_enable_postgis.py`
4. `docker compose up -d` (if not running)
5. `alembic upgrade head`
6. Verify: `docker exec wandr_postgres psql -U wandr -d wandr -c "\dx"`
7. Update `docs/context.md` (step ✅, next 1.4a)

**Rollback:** `alembic downgrade base` removes revision tracking only; extensions remain (by design).

## Open Questions

- None for 1.3 — step doc is prescriptive and aligns with existing infrastructure.
