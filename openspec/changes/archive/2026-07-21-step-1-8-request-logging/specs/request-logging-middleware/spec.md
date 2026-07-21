## ADDED Requirements

### Requirement: Request ID generation and propagation
The request logging middleware SHALL assign an `X-Request-ID` for every HTTP request. If the inbound request already includes an `X-Request-ID` header, the middleware MUST preserve that value; otherwise it MUST generate a new UUID string.

#### Scenario: Generated request ID
- **WHEN** a client calls `GET /api/v1/health` without an `X-Request-ID` header
- **THEN** the response includes an `X-Request-ID` header whose value is a non-empty UUID string

#### Scenario: Propagated request ID
- **WHEN** a client calls `GET /api/v1/health` with `X-Request-ID: my-trace-id-42`
- **THEN** the response `X-Request-ID` header equals `my-trace-id-42`

### Requirement: Structlog request context binding
At the start of each request the middleware MUST clear structlog contextvars, then bind `request_id`, `method`, and `path` so subsequent log lines for that request share the same request identity. The middleware MUST NOT log request or response bodies.

#### Scenario: Context cleared and rebound
- **WHEN** two sequential requests are handled by the same worker
- **THEN** logs for the second request use that request's `request_id` and do not retain the first request's contextvars

### Requirement: Latency logging and exception pass-through
The middleware SHALL log `request.start` before invoking the next handler. On success it SHALL log `request.end` with `status_code` and `latency_ms` (measured with `time.perf_counter()`). On unhandled exception it SHALL log `request.error` with `latency_ms` and re-raise the exception without swallowing it.

#### Scenario: Successful request logs
- **WHEN** `GET /api/v1/health` returns successfully
- **THEN** server logs include `request.start` and `request.end` sharing the same `request_id`, and `request.end` includes `status_code` and `latency_ms`

#### Scenario: Exception still propagates
- **WHEN** a downstream handler raises an unhandled exception
- **THEN** the middleware logs `request.error` with `latency_ms` and the exception continues to the global exception handlers

### Requirement: Outermost middleware registration
`create_app()` SHALL register `RequestLoggingMiddleware` via `add_middleware` so it is the outermost middleware layer for requests (last-added under Starlette LIFO stacking for this change).

#### Scenario: Middleware active on health
- **WHEN** the app is created and a client hits `/api/v1/health`
- **THEN** the response includes `X-Request-ID` (proving the middleware ran)
