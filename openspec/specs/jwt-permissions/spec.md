## Purpose

HS256 JWT creation/verification and FastAPI auth dependencies (Bearer header or `wandr_token` cookie).

## Requirements

### Requirement: Create and verify HS256 access tokens
The system SHALL create signed HS256 JWTs with claims `sub` (user id string), `email`, and `exp`, using `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_DAYS` from `get_settings()`. `verify_token` MUST return a `TokenPayload` on success and MUST return `None` on any failure (expired, malformed, missing claims) without raising.

#### Scenario: Round-trip valid token
- **WHEN** `create_access_token(user_id, email)` is called and the result is passed to `verify_token`
- **THEN** the payload `user_id` and `email` match the inputs and `exp` is timezone-aware UTC

#### Scenario: Invalid or expired token returns None
- **WHEN** `verify_token` receives an empty string, garbage JWT, or an expired token
- **THEN** the function returns `None` and does not raise

### Requirement: Require auth FastAPI dependency
The system SHALL provide `require_auth` that resolves a bearer token from the `Authorization` header, or if absent from the `wandr_token` cookie, verifies it, and returns `TokenPayload`. Missing or invalid tokens MUST raise `UnauthorizedError` (401), never FastAPI’s default OAuth error or `HTTPException`.

#### Scenario: Missing token
- **WHEN** a protected dependency runs with no Authorization header and no `wandr_token` cookie
- **THEN** `UnauthorizedError` is raised with message indicating authentication is required

#### Scenario: Invalid token
- **WHEN** a protected dependency receives a non-verifiable token via header or cookie
- **THEN** `UnauthorizedError` is raised for invalid or expired token

### Requirement: Optional auth FastAPI dependency
The system SHALL provide `optional_auth` that returns `TokenPayload` when a valid token is present (Bearer header preferred, else `wandr_token` cookie) and returns `None` for guests. It MUST never raise for missing or invalid tokens.

#### Scenario: Guest access
- **WHEN** no Authorization header and no valid `wandr_token` cookie are present
- **THEN** `optional_auth` returns `None`

#### Scenario: Cookie-authenticated user
- **WHEN** `wandr_token` holds a valid JWT and no Authorization header is set
- **THEN** `optional_auth` returns the matching `TokenPayload`

### Requirement: Convenience user id dependency
The system SHALL provide `get_current_user_id` that depends on `require_auth` and returns the payload’s `user_id` UUID.

#### Scenario: Extract user id
- **WHEN** `get_current_user_id` runs with a valid authenticated payload
- **THEN** it returns that payload’s `user_id`
