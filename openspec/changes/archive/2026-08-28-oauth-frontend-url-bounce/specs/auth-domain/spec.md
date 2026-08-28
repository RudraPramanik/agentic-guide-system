## MODIFIED Requirements

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

