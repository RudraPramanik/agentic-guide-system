## ADDED Requirements

### Requirement: CORS middleware uses explicit credentialed origins
The application SHALL load `CORS_ALLOWED_ORIGINS: list[str]` via `get_settings()` and register FastAPI `CORSMiddleware` in `create_app()` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_origins` equal to that settings list.

Default origins MUST include `http://localhost:3000`. Origins MUST NOT include `*` while credentials are enabled. Origins MUST NOT be hardcoded as production domain strings inside `main.py`.

Auth cookie SameSite code MUST NOT change in this capability.

#### Scenario: App starts with CORS configured
- **WHEN** `create_app()` is called with default settings
- **THEN** the app is created successfully and `CORS_ALLOWED_ORIGINS` is a list that does not contain `*`

#### Scenario: Configured browser origin is allowed
- **WHEN** a TestClient (or equivalent) request includes `Origin: http://localhost:3000` against a public route
- **THEN** the response includes `Access-Control-Allow-Origin` for that origin (or equivalent CORS allow behavior for the middleware stack)

#### Scenario: Empty origins list does not crash startup
- **WHEN** `CORS_ALLOWED_ORIGINS` is an empty list
- **THEN** `create_app()` still succeeds (no cross-origin allow)
