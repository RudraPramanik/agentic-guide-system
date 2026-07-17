## Purpose

Unit and API test coverage for JWT, permissions, and the auth domain (Google OAuth + guest session). No email/password signup surface.

## Requirements

### Requirement: JWT unit coverage
Tests SHALL cover `create_access_token` / `verify_token` round-trip, rejection of invalid tokens (returns `None`), and rejection of expired tokens (returns `None`).

#### Scenario: Round-trip
- **WHEN** a token is created for a known user id and email
- **THEN** `verify_token` returns matching `user_id` and `email`

### Requirement: Permissions unit coverage
Tests SHALL cover `_extract_token` / `require_auth` / `optional_auth` for: missing token, Bearer header, `wandr_token` cookie, Bearer preferred over cookie, and invalid token behavior (`require_auth` raises 401 path; `optional_auth` returns `None`).

#### Scenario: Cookie auth
- **WHEN** `optional_auth` receives a request with only a valid `wandr_token` cookie
- **THEN** it returns a `TokenPayload`

### Requirement: Auth schema and exception unit coverage
Tests SHALL assert guest `AuthMeResponse` shape and that `GoogleOAuthError` / `InvalidTokenError` / `AccountInactiveError` expose the expected status codes and service details.

#### Scenario: GoogleOAuthError
- **WHEN** `GoogleOAuthError` is constructed
- **THEN** `status_code` is 502 and details include `service=google_oauth`

### Requirement: UserRepository unit coverage
Tests SHALL verify `get_by_email` and `get_by_google_id` return matching users and exclude soft-deleted rows, using the test DB session.

#### Scenario: Soft-deleted excluded
- **WHEN** a user is soft-deleted
- **THEN** `get_by_email` for that email returns `None`

### Requirement: AuthService unit coverage with mocked Google
Tests SHALL cover `upsert_google_user` create/update paths and Google HTTP mapping: 401 → `UnauthorizedError`, exhausted network failure → `GoogleOAuthError`, without calling the real Google APIs.

#### Scenario: Rejected Google token
- **WHEN** userinfo returns HTTP 401
- **THEN** `verify_google_token` raises `UnauthorizedError`

### Requirement: Auth API feature coverage
API tests SHALL cover guest `/api/v1/auth/me` (session cookie set), `/api/v1/auth/logout`, `/api/v1/auth/google` when OAuth is not configured, and authenticated `/me` via `wandr_token` cookie for an active seeded user.

#### Scenario: Guest me
- **WHEN** GET `/api/v1/auth/me` has no auth
- **THEN** body has `is_guest=true`, `user=null`, non-empty `session_id`, and `Set-Cookie` includes httpOnly `wandr_session`

#### Scenario: Cookie-authenticated me
- **WHEN** GET `/api/v1/auth/me` includes a valid `wandr_token` for an active DB user
- **THEN** body has `is_guest=false` and a `user` object

### Requirement: No email-password signup surface
The auth test suite SHALL NOT introduce or require email/password signup endpoints; coverage reflects Google OAuth + guest session only.

#### Scenario: No password register route
- **WHEN** the OpenAPI/routes of the test app are inspected for auth paths
- **THEN** there is no password-based register/login route under `/api/v1/auth`
