## 1. Dependencies

- [ ] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step1.md` §1.3 before coding
- [ ] 1.2 Append `alembic==1.18.4` and `geoalchemy2==0.20.0` to `requirements.txt` with step 1.3 comments
- [ ] 1.3 Run `pip install alembic==1.18.4 geoalchemy2==0.20.0`

## 2. Alembic configuration

- [ ] 2.1 Replace placeholder `alembic.ini`: `script_location = alembic`, UTC timezone, date-prefixed `file_template`, `prepend_sys_path = .` — no `sqlalchemy.url`
- [ ] 2.2 Replace placeholder `alembic/env.py` with async env per step 1.3: `get_settings()` URL injection, `Base.metadata`, `geoalchemy2` import, empty model-import block
- [ ] 2.3 Create `alembic/versions/` directory if missing

## 3. Migration 001 — PostGIS

- [ ] 3.1 Create `alembic/versions/001_enable_postgis.py` (revision `001`, `down_revision = None`)
- [ ] 3.2 Implement upgrade: `CREATE EXTENSION IF NOT EXISTS` for `postgis`, `postgis_topology`, `uuid-ossp`
- [ ] 3.3 Implement downgrade as no-op (`pass`)

## 4. Validation

- [ ] 4.1 Ensure Docker Postgres is up (`docker compose up -d`) and `python scripts/test_db_conn.py` passes
- [ ] 4.2 Run `alembic upgrade head` — expect `Running upgrade  -> 001, Enable PostGIS extensions`
- [ ] 4.3 Verify extensions: `docker exec wandr_postgres psql -U wandr -d wandr -c "\dx"` shows `postgis`, `postgis_topology`, `uuid-ossp`
- [ ] 4.4 Confirm `src/main.py` does not invoke Alembic at startup

## 5. Context checkpoint

- [ ] 5.1 Update `docs/context.md`: Last updated, Next step → 1.4a, mark 1.3 ✅, note `alembic/env.py` is real (remove from stubs), add migration tooling to Implemented modules if appropriate
