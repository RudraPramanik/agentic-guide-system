## Purpose

Auth domain: Pydantic schemas, typed exceptions, UserRepository, AuthService (Google OAuth), and `/api/v1/auth` routes. Login is Google OAuth only; guests use session cookies.

## Requirements

### Requirement: Auth schemas and exceptions
The system SHALL expose Pydantic schemas `UserOut`, `AuthMeResponse`, `TokenResponse`, and `GoogleCallbackParams` with no imports from auth models or repositories. Auth-specific exceptions `GoogleOAuthError`, `InvalidTokenError`, and `AccountInactiveError` MUST inherit from existing `WandrError` subclasses only (never `HTTPException`).

#### Scenario: Guest AuthMeResponse
- **WHEN** `AuthMeResponse(is_guest=True, session_id=...)` is constructed without a user
- **THEN** `user` is `None` and `is_guest` is true

#### Scenario: GoogleOAuthError status
- **WHEN** `GoogleOAuthError` is raised
- **THEN** `status_code` is 502 and details include `service=google_oauth`

### Requirement: User repository lookups
`UserRepository` SHALL extend `BaseRepository[User, UUID]` and provide soft-delete-aware `get_by_email` and `get_by_google_id` that return `None` when no active row matches.

#### Scenario: Soft-deleted users excluded
- **WHEN** a user matching email or google_id has `deleted_at` set
- **THEN** the corresponding get method returns `None`

### Requirement: Upsert Google user
`AuthService.upsert_google_user` SHALL find by `google_id`, else by email, else create; update `google_id` / `avatar_url` when changed; then commit and refresh. This commit-in-service behavior is auth-only.

#### Scenario: New Google user
- **WHEN** no user exists for the google_id or email
- **THEN** a new active user is created and returned after commit

#### Scenario: Link existing email user
- **WHEN** a user exists by email but not google_id
- **THEN** the user is updated with the google_id (and avatar if changed) and returned

### Requirement: Google OAuth HTTP calls
`AuthService` SHALL exchange authorization codes and fetch Google userinfo using httpx with explicit connect/read timeouts and tenacity retries on connect/timeout only. Rejected tokens (400/401) MUST map to `UnauthorizedError` without retry. Exhausted network/HTTP failures MUST raise `GoogleOAuthError`. Google endpoint URLs MUST come from `get_settings()`.

#### Scenario: Google rejects token
- **WHEN** Google userinfo returns 401
- **THEN** `UnauthorizedError` is raised and the call is not retried as success

#### Scenario: Google unavailable after retries
- **WHEN** Google token exchange fails with repeated timeouts
- **THEN** `GoogleOAuthError` is raised (502 path)

### Requirement: Start Google OAuth
`GET /api/v1/auth/google` SHALL return `ApiResponse` explaining OAuth is not configured when `GOOGLE_CLIENT_ID` is empty; otherwise redirect to Google’s authorize URL with scopes `openid email profile`.

#### Scenario: OAuth not configured
- **WHEN** `GOOGLE_CLIENT_ID` is empty
- **THEN** the response is a successful `ApiResponse` whose data indicates Google OAuth is not configured

### Requirement: OAuth callback
`GET /api/v1/auth/callback` SHALL exchange the code, fetch userinfo, upsert the user, issue a JWT, and set httpOnly `wandr_token`. When `FRONTEND_URL` is configured, success MUST redirect the browser to `{FRONTEND_URL}/auth/done` with the cookie set on the redirect response (not return JSON on the API host). When `FRONTEND_URL` is empty, success MAY return `ApiResponse[TokenResponse]` JSON with Set-Cookie (local debugging fallback). On Google `error` query param or any `WandrError` during the flow, when `FRONTEND_URL` is configured the handler MUST redirect to `{FRONTEND_URL}/auth/error?reason=…`; when `FRONTEND_URL` is empty it MUST redirect to `/auth/error?reason=…` on the API host. Handlers MUST use a single `AuthService` instance per request.

#### Scenario: Happy-path redirect to frontend
- **WHEN** callback completes successfully and `FRONTEND_URL` is set
- **THEN** the client receives HTTP 302 to `{FRONTEND_URL}/auth/done` and `wandr_token` is set httpOnly with SameSite=lax and secure only in production

#### Scenario: JSON fallback without frontend URL
- **WHEN** callback completes successfully and `FRONTEND_URL` is empty
- **THEN** response body includes access token and user as `ApiResponse[TokenResponse]`, and `wandr_token` cookie is set httpOnly

#### Scenario: OAuth failure redirects to frontend
- **WHEN** token exchange raises `GoogleOAuthError` and `FRONTEND_URL` is set
- **THEN** the client is redirected to `{FRONTEND_URL}/auth/error?reason=oauth_failed`

#### Scenario: OAuth failure on API host without frontend URL
- **WHEN** token exchange raises `GoogleOAuthError` and `FRONTEND_URL` is empty
- **THEN** the client is redirected to `/auth/error?reason=oauth_failed`

### Requirement: Current user or guest me endpoint
`GET /api/v1/auth/me` SHALL use `optional_auth`. Guests and authenticated users MUST receive/ensure an httpOnly `wandr_session` cookie and return `AuthMeResponse` with `session_id` in the JSON body. Authenticated inactive users MUST raise `AccountInactiveError`; missing user for a valid token MUST raise `UnauthorizedError`.

#### Scenario: Guest me
- **WHEN** `/api/v1/auth/me` is called without a valid token
- **THEN** response data has `is_guest=true`, `user=null`, and a non-empty `session_id`, and `wandr_session` is set httpOnly

#### Scenario: Authenticated me via cookie
- **WHEN** a valid `wandr_token` cookie is present for an active user
- **THEN** response data has `is_guest=false` and a `UserOut` payload

### Requirement: Logout
`POST /api/v1/auth/logout` SHALL delete the `wandr_token` cookie without requiring authentication and return `ApiResponse` confirming logout.

#### Scenario: Logout without prior login
- **WHEN** logout is called with no auth cookies
- **THEN** the response is successful and instructs that the client is logged out

### Requirement: Router registration and layering
The auth router MUST be registered in `create_app()` under `/api/v1/auth`. Router handlers MUST call `AuthService` only (never `UserRepository` or the DB session for queries). All successful JSON endpoints MUST return `ApiResponse[T]`.

#### Scenario: Router mounted
- **WHEN** the FastAPI app is created
- **THEN** auth routes are available under `/api/v1/auth`
