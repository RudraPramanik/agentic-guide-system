## MODIFIED Requirements

### Requirement: CORS middleware uses explicit credentialed origins
The application SHALL load `CORS_ALLOWED_ORIGINS: list[str]` via `get_settings()` and register FastAPI `CORSMiddleware` in `create_app()` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_origins` equal to that settings list.

Default origins MUST include both `http://localhost:3000` and `http://127.0.0.1:3000`. Origins MUST NOT include `*` while credentials are enabled. Origins MUST NOT be hardcoded as production domain strings inside `main.py`.

Auth cookie SameSite code MUST NOT change in this capability. Listing both loopback frontend origins MUST NOT be treated as merging cookie jars: `localhost` and `127.0.0.1` remain different hosts for `wandr_session`.

#### Scenario: App starts with CORS configured
- **WHEN** `create_app()` is called with default settings
- **THEN** the app is created successfully and `CORS_ALLOWED_ORIGINS` is a list that does not contain `*`
- **AND** the default list includes `http://localhost:3000` and `http://127.0.0.1:3000`

#### Scenario: Configured browser origin is allowed
- **WHEN** a TestClient (or equivalent) request includes `Origin: http://localhost:3000` against a public route
- **THEN** the response includes `Access-Control-Allow-Origin` for that origin (or equivalent CORS allow behavior for the middleware stack)

#### Scenario: Loopback IPv4 frontend origin is allowed
- **WHEN** a TestClient (or equivalent) request includes `Origin: http://127.0.0.1:3000` against a public route under default settings
- **THEN** the response includes `Access-Control-Allow-Origin` for `http://127.0.0.1:3000` (or equivalent CORS allow behavior for the middleware stack)

#### Scenario: Empty origins list does not crash startup
- **WHEN** `CORS_ALLOWED_ORIGINS` is an empty list
- **THEN** `create_app()` still succeeds (no cross-origin allow)
