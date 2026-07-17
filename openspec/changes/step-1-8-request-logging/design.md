## Context

P1 JWT + auth domain are complete and registered. `src/core/middleware/logging.py` is still a one-line stub from step 0.1. Blueprint middleware chain order is: request_id/logging → auth → rate_limit → handler. Step 1.8 in `docs/steps/step1.md` implements the outermost link: `RequestLoggingMiddleware`. No new packages; structlog is already configured in P0.

## Goals / Non-Goals

**Goals:**
- Every response carries `X-Request-ID` (generated UUID or propagated from inbound header)
- structlog contextvars bind `request_id`, `method`, `path` for the request lifetime
- Log `request.start` and `request.end` (or `request.error`) with `latency_ms` via `time.perf_counter()`
- Middleware registered outermost in Starlette (added last with `add_middleware`)

**Non-Goals:**
- Rate limit middleware (1.10), TripEditEvent (1.9)
- Logging request/response bodies (PII risk)
- New env vars or package installs
- Automated pytest for header asserts (deferred until after 1.8/1.10 per context.md)

## Decisions

### D1 — Follow step 1.8 implementation literally
- **Why:** Prompt already specifies `BaseHTTPMiddleware`, contextvars clear/bind, start/end/error events, and re-raise on exception.
- **Alt:** Pure ASGI middleware — unnecessary complexity for this step; stick to the step contract.

### D2 — Outermost = `add_middleware` last
- Starlette stacks middleware LIFO. Auth/rate-limit will be added later with earlier `add_middleware` calls so logging stays outermost.
- For this change only: register `RequestLoggingMiddleware` after app creation, before routers (as step says). When 1.10 lands, add rate limit *before* logging in source order so logging remains last-added.

### D3 — Preserve inbound `X-Request-ID` as-is
- Do not normalize/rewrite if the client or gateway already set it — supports distributed tracing.
- Empty/missing → `str(uuid.uuid4())`.

### D4 — Clear contextvars at every request start
- Mandatory to prevent async worker context leak across requests.
- Bind only `request_id`, `method`, `path` — no user PII in middleware.

### D5 — Never swallow exceptions
- On failure: log `request.error` with `latency_ms` + `exc_info=True`, then re-raise so global exception handlers still run.

### D6 — No new settings
- Step 1.8 needs no env vars. Middleware uses existing structlog setup from lifespan/`configure_logging()`.

## Risks / Trade-offs

- [BaseHTTPMiddleware known edge cases with streaming] → Accept for P1; revisit if SSE planner streaming misbehaves later
- [Context leak if clear_contextvars skipped] → Treat clear as mandatory in code review / validation
- [Header case sensitivity] → Starlette normalizes; step validation uses case-insensitive grep/`Select-String`
- [No automated test in this change] → Manual curl validation per step; pytest header asserts land after 1.10

## Migration Plan

1. Implement `RequestLoggingMiddleware` in `src/core/middleware/logging.py`
2. Register in `create_app()` via `app.add_middleware(RequestLoggingMiddleware)`
3. Validate with curl health checks (header present + custom ID preserved + log lines)
4. Update `docs/context.md` (Next step → 1.9; mark 1.8 ✅; remove middleware from stubs)
5. Rollback: revert the two files; no DB/migration impact

## Open Questions

- None blocking for 1.8.
