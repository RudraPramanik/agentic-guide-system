## 1. Tooling + test database

- [x] 1.1 Append pytest deps to `requirements.txt` with why-comments; install `pytest==9.1.0`, `pytest-asyncio==1.4.0`, `pytest-mock==3.15.1`
- [x] 1.2 Create root `pytest.ini` (`asyncio_mode=auto`, `testpaths=tests`)
- [x] 1.3 Create Postgres DB `wandr_test` (`docker exec wandr_postgres psql -U wandr -c "CREATE DATABASE wandr_test;"`) if missing

## 2. Harness

- [x] 2.1 Replace stub `tests/conftest.py` with `test_engine`, `db_session` (rollback), `client` (ASGI + `get_db` override), `auth_token`, `auth_headers`
- [x] 2.2 Verify harness: `pytest tests/core/test_exceptions.py -v` still passes

## 3. Unit tests

- [x] 3.1 Add `tests/core/test_jwt.py` — round-trip, invalid, expired
- [x] 3.2 Add `tests/core/test_permissions.py` — Bearer, cookie, preference, require vs optional
- [x] 3.3 Add `tests/auth/test_schemas_exceptions.py` — guest response + exception hierarchy
- [x] 3.4 Add `tests/auth/test_repository.py` — get_by_email / get_by_google_id + soft-delete exclusion
- [x] 3.5 Add `tests/auth/test_service.py` — upsert paths + mocked Google 401 / network → typed errors

## 4. API / feature tests

- [x] 4.1 Add `tests/auth/test_auth_router.py` — health, guest `/me` (+ session cookie), logout, google not-configured
- [x] 4.2 Add cookie-authenticated `/me` test with seeded active user (omit middleware header tests until 1.8/1.10)
- [x] 4.3 Run `pytest tests/ -v` — all green

## 5. Context

- [x] 5.1 Update `docs/context.md` — note pytest harness + auth tests; mark 1.11 done for harness/auth coverage (middleware assertions still pending); keep **Next step: 1.8**
