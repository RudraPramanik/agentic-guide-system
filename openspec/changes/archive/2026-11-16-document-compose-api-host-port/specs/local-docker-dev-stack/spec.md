## REMOVED Requirements

### Requirement: API container runs uvicorn with reload on published port 8000
**Reason**: Root Compose already publishes `8001:8000`. Requiring host port 8000 contradicts the file and the living docs that agents follow.
**Migration**: Use the replacement requirement. Container bind stays `0.0.0.0:8000`. Host URLs for the Compose stack are `http://localhost:8001`.

## ADDED Requirements

### Requirement: API container runs uvicorn with reload on published host port 8001
The local API service MUST run uvicorn for `src.main:app` bound to `0.0.0.0:8000` with reload enabled for source changes, and MUST wait until Postgres is healthy before serving. Host port **8001** MUST be published to container port 8000. `docs/app/system.md` (local infrastructure) and `docs/context.md` (local dev quick ref, including port-clash and compose-down notes) MUST give health and OpenAPI as `http://localhost:8001/api/v1/health` and `http://localhost:8001/docs`. Those sections MUST NOT tell the reader to free host port 8000 before `docker compose up`, or that Compose binds host port 8000. An optional host uvicorn process that is started only while the Compose API service is stopped MAY keep port 8000; that path is not the Compose publish.

#### Scenario: Host health and docs use 8001
- **WHEN** the local Compose stack is up
- **THEN** `http://localhost:8001/docs` and `http://localhost:8001/api/v1/health` are the host URLs, and the container process is still listening on port 8000

#### Scenario: Living local docs match the publish
- **WHEN** a reader opens the local infrastructure section of `docs/app/system.md` and the local dev quick ref in `docs/context.md`
- **THEN** the API host port is 8001 and neither section says Compose publishes or clashes on host port 8000

#### Scenario: Source change reloads without rebuild
- **WHEN** a Python file under the bind-mounted application source changes while the API service is running
- **THEN** uvicorn reloads the process without requiring a Compose rebuild
