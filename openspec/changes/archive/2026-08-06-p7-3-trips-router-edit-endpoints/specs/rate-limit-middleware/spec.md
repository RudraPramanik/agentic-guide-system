## ADDED Requirements

### Requirement: User-keyed trip-edit rate limit dependency

The system SHALL provide Settings fields `RATE_LIMIT_TRIP_EDIT_REQUESTS` (default 20) and `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` (default 60) via `get_settings()`. The system SHALL expose a FastAPI dependency `rate_limit_trip_edit` that Depends on `require_auth`, calls `get_rate_limiter().is_allowed` with key `"{user_id}:trip_edit"` and the trip-edit settings limits, and returns the `TokenPayload` when allowed. When not allowed, it MUST raise a `WandrError` (preferably `RateLimitedError`) with `status_code=429` and `code="rate_limit_exceeded"`. When the limiter backend raises, the dependency MUST fail open (return payload; do not block the request). Trip-edit UUID paths MUST NOT be added to `_route_limit_table`; middleware IP/path default MAY still apply (dual limit is acceptable). Router handlers for the four edit endpoints MUST Depends on `rate_limit_trip_edit` (not bare `require_auth` alone).

#### Scenario: Settings expose trip-edit limits

- **WHEN** `get_settings()` is loaded after step 7.3
- **THEN** `RATE_LIMIT_TRIP_EDIT_REQUESTS` defaults to 20 and `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` defaults to 60

#### Scenario: Exceeding user-keyed edit limit returns 429

- **WHEN** the same authenticated user exceeds the trip-edit request limit within the window (e.g. 21st call with a mock limiter)
- **THEN** the edit endpoint returns HTTP 429 with `code="rate_limit_exceeded"` and the trip is unchanged

#### Scenario: Limiter exception fails open on edit dependency

- **WHEN** `get_rate_limiter().is_allowed` raises during `rate_limit_trip_edit`
- **THEN** the dependency allows the request to proceed (does not raise 429/500 from the limiter failure alone)

#### Scenario: Edit paths absent from route limit table

- **WHEN** `_route_limit_table()` is inspected after step 7.3
- **THEN** it does not contain UUID-templated trip edit path entries
