## MODIFIED Requirements

### Requirement: OAuth callback
`GET /api/v1/auth/callback` SHALL exchange the code, fetch userinfo, upsert the user, issue a JWT, and set httpOnly `wandr_token`. When `FRONTEND_URL` is configured, success MUST redirect the browser to `{FRONTEND_URL}/auth/done` with the cookie set on the redirect response (not return JSON on the API host). When `FRONTEND_URL` is empty, success MAY return `ApiResponse[TokenResponse]` JSON with Set-Cookie (local debugging fallback). On Google `error` query param or any `WandrError` during the flow, when `FRONTEND_URL` is configured the handler MUST redirect to `{FRONTEND_URL}/auth/error?reason=…`; when `FRONTEND_URL` is empty it MUST redirect to `/auth/error?reason=…` on the API host. Handlers MUST use a single `AuthService` instance per request.

Cookie flags for `wandr_token` and `wandr_session` set by auth routes MUST be: `HttpOnly`; `Secure` when `ENVIRONMENT=production`; `SameSite=None` when `ENVIRONMENT=production` and `SameSite=Lax` otherwise.

#### Scenario: Happy-path redirect to frontend
- **WHEN** callback completes successfully and `FRONTEND_URL` is set
- **THEN** the client receives HTTP 302 to `{FRONTEND_URL}/auth/done` and `wandr_token` is set httpOnly

#### Scenario: Production cookies are cross-site capable
- **WHEN** `ENVIRONMENT=production` and auth sets `wandr_token` or `wandr_session`
- **THEN** Set-Cookie includes `SameSite=None` and `Secure`

#### Scenario: Non-production cookies stay Lax
- **WHEN** `ENVIRONMENT` is not `production` and auth sets those cookies
- **THEN** Set-Cookie uses `SameSite=Lax`

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
`GET /api/v1/auth/me` SHALL use `optional_auth`. Guests and authenticated users MUST receive/ensure an httpOnly `wandr_session` cookie and return `AuthMeResponse` with `session_id` in the JSON body. Authenticated inactive users MUST raise `AccountInactiveError`; missing user for a valid token MUST raise `UnauthorizedError`. Cookie flags MUST match the OAuth callback production/non-production SameSite and Secure rules.

#### Scenario: Guest me
- **WHEN** `/api/v1/auth/me` is called without a valid token
- **THEN** response data has `is_guest=true`, `user=null`, and a non-empty `session_id`, and `wandr_session` is set httpOnly

#### Scenario: Authenticated me via cookie
- **WHEN** a valid `wandr_token` cookie is present for an active user
- **THEN** response data has `is_guest=false` and a `UserOut` payload

### Requirement: Logout
`POST /api/v1/auth/logout` SHALL delete the `wandr_token` cookie without requiring authentication and return `ApiResponse` confirming logout. Delete-cookie attributes MUST use the same `SameSite` and `Secure` policy as set-cookie for the current environment so browsers clear the production cross-site cookie.

#### Scenario: Logout without prior login
- **WHEN** logout is called with no auth cookies
- **THEN** the response is successful and instructs that the client is logged out
