## ADDED Requirements

### Requirement: Catalog API boots without LLM_API_KEY
Settings load used by Alembic migrate-then-serve and by uvicorn MUST succeed when `LLM_API_KEY` is unset, commented, or empty, provided other required settings (including `SECRET_KEY`, `DATABASE_URL`, and `NOMINATIM_USER_AGENT`) are present. The local Compose API process MUST bind the published API port so catalog routes remain reachable. Application code MUST continue to read env only through `get_settings()`.

#### Scenario: Compose api binds port without LLM_API_KEY
- **WHEN** the local API service starts with `LLM_API_KEY` unset, commented, or empty in `.env`, and other required settings are present
- **THEN** the process MUST complete migrate-then-serve and bind host `:8000`, and `GET /api/v1/health` and `GET /api/v1/destinations/search` MUST be reachable (not `ERR_CONNECTION_REFUSED`)

#### Scenario: Sibling FE CONNECTION_REFUSED is not caused by missing LLM key alone
- **WHEN** Postgres/Qdrant/Redis are healthy and the API process is running without `LLM_API_KEY`
- **THEN** destination search against `http://localhost:8000` MUST connect; operator docs MUST state that missing `LLM_API_KEY` no longer explains catalog `:8000` refusal — check `docker compose ps` / `docker logs wandr_api` for other boot failures

### Requirement: Empty LLM_API_KEY fails at the LLM gateway only
Calls that go through the sole LLM gateway MUST fail fast with `WandrLLMError` (`llm_unavailable`) when `LLM_API_KEY` is missing or whitespace-only, naming `LLM_API_KEY` and the Compose `.env` / `.env.example`. Catalog and health routes MUST NOT call the LLM gateway. Generate and enrich paths that already treat `WandrLLMError` as fail-soft MUST keep that behavior.

#### Scenario: chat_completion refuses empty key before provider call
- **WHEN** `LLM_API_KEY` is empty or whitespace-only and a caller invokes the LLM gateway
- **THEN** the gateway MUST raise `WandrLLMError` with code `llm_unavailable` without calling the provider, and the message MUST mention `LLM_API_KEY` and `.env`

### Requirement: Other missing required env still fails boot with an operator-readable message
When truly required Settings fields other than `LLM_API_KEY` are missing, Settings load MUST fail fast with an operator-readable message that names the missing field(s) and points at the Compose `env_file` `.env` (see `.env.example`).

#### Scenario: Missing DATABASE_URL still exits before bind
- **WHEN** the local API service starts without `DATABASE_URL`
- **THEN** the process MUST exit before binding the published API port, and the logs MUST name `DATABASE_URL` and the `.env` `env_file`
