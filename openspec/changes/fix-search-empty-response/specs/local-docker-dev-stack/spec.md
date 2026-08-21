## ADDED Requirements

### Requirement: Local API reload watches application source only
The Compose `api` uvicorn `--reload` process MUST watch the bind-mounted application package (`/app/src`) only. It MUST NOT watch the entire `/app` tree (scripts, alembic cwd noise, mounted `.env`). A Python change under `src/` MUST still reload without a Compose rebuild.

#### Scenario: Reload dir is application source
- **WHEN** the local API service is started via Compose
- **THEN** uvicorn reload is configured with `--reload-dir` pointing at `/app/src` (or equivalent), not the whole `/app` working directory

#### Scenario: Source change still reloads
- **WHEN** a Python file under the bind-mounted `src/` tree changes while the API service is running
- **THEN** uvicorn reloads the process without a Compose rebuild
