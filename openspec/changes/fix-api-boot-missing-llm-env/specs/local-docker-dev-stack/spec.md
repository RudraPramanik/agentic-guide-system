## ADDED Requirements

### Requirement: Missing required env fails boot with an operator-readable message
Settings load (used by Alembic migrate-then-serve and by uvicorn) MUST fail fast when required fields are missing, including `LLM_API_KEY`. The failure MUST name the missing field(s) and MUST tell the operator to set them in the Compose `env_file` `.env` (see `.env.example`). `LLM_API_KEY` MUST remain required even for catalog routes that do not call the LLM. Application code MUST continue to read env only through `get_settings()`.

#### Scenario: Compose api exits when LLM_API_KEY is missing
- **WHEN** the local API service starts with `LLM_API_KEY` unset or commented in `.env`
- **THEN** the process MUST exit before binding the published API port, and the logs MUST name `LLM_API_KEY` and the `.env` `env_file` (not only a raw missing-field traceback)

#### Scenario: Frontend CONNECTION_REFUSED maps to API not listening
- **WHEN** Postgres/Qdrant/Redis are up but the API process exited for missing required env
- **THEN** `GET /api/v1/health` and `GET /api/v1/destinations/search` on host `:8000` MUST fail to connect, and operator docs MUST state that sibling-frontend `ERR_CONNECTION_REFUSED` to `:8000` means `wandr_api` is not listening — not a frontend URL bug
