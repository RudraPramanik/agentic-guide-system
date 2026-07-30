## ADDED Requirements

### Requirement: Credentialed CORS from settings

The application MUST register FastAPI `CORSMiddleware` in `create_app()` with `allow_origins` taken from `get_settings().CORS_ALLOWED_ORIGINS` (a list of strings), `allow_credentials=True`, and MUST NOT use `allow_origins=["*"]` while credentials are enabled.

#### Scenario: Configured origin is allowed
- **WHEN** `CORS_ALLOWED_ORIGINS` includes `http://localhost:3000` and a browser sends an Origin of that value
- **THEN** the CORS response headers MUST permit that origin with credentials

#### Scenario: Wildcard forbidden with credentials
- **WHEN** settings are defined for production-safe CORS
- **THEN** `CORS_ALLOWED_ORIGINS` MUST be an explicit list and MUST NOT be the single wildcard `*` while `allow_credentials` is true

### Requirement: Origins are not hardcoded in middleware call site

CORS allowed origins MUST be read via `get_settings()` only — no hardcoded production domain strings in `main.py` beyond what settings provides.

#### Scenario: Env-driven origins
- **WHEN** the operator changes `CORS_ALLOWED_ORIGINS` in environment/settings
- **THEN** the running app's CORS allow list MUST reflect that configuration without code edits
