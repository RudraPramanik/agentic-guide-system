## ADDED Requirements

### Requirement: IP-keyed destination-prepare rate limit dependency

The system SHALL provide Settings fields `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` (default 5) and `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` (default 60) via `get_settings()`. The prepare HTTP handler MUST apply an IP-keyed limiter dependency (key pattern `{ip}:dest_prepare`) using `get_rate_limiter().is_allowed`. When not allowed, it MUST raise `RateLimitedError` (HTTP 429, code `rate_limit_exceeded`). When the limiter backend raises, the dependency MUST fail open. The UUID prepare path MUST NOT be added to `_route_limit_table` (exact path match cannot key UUID routes). Existing planner (10/min) and destinations-search (20/min) table rows MUST remain unchanged.

#### Scenario: Settings expose prepare limits

- **WHEN** `get_settings()` is loaded after this change
- **THEN** `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` defaults to 5 and `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` defaults to 60

#### Scenario: Exceeding prepare limit returns 429

- **WHEN** the same client IP exceeds the prepare request limit within the window
- **THEN** a subsequent prepare returns HTTP 429 with `code="rate_limit_exceeded"` and no new scrape is started

#### Scenario: Limiter exception fails open on prepare

- **WHEN** `get_rate_limiter().is_allowed` raises during the prepare limiter
- **THEN** the request proceeds (does not fail 429/500 from the limiter failure alone)

#### Scenario: Prepare UUID path absent from route limit table

- **WHEN** `_route_limit_table()` is inspected after this change
- **THEN** it does not contain a UUID-templated destinations prepare path
