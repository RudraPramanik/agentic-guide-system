## Why

P1 auth and JWT are done; the next gate is request observability before TripEditEvent and rate limiting. Step 1.8 in `docs/steps/step1.md` adds the outermost middleware that assigns/propagates `X-Request-ID` and logs per-request latency — required so later middleware and domain logs share a correlatable request context.

## What Changes

- Implement **step 1.8** — replace stub `src/core/middleware/logging.py` with `RequestLoggingMiddleware`
- Register the middleware in `src/main.py` as the outermost layer (added last via `add_middleware`)
- Propagate or generate `X-Request-ID`, bind structlog contextvars, log `request.start` / `request.end` (or `request.error`) with `latency_ms`
- Echo `X-Request-ID` on every response; never log request/response bodies

## Capabilities

### New Capabilities

- `request-logging-middleware`: Per-request ID generation/propagation, structlog context binding, latency logging, response header echo

### Modified Capabilities

- (none)

## Impact

- **Code:** `src/core/middleware/logging.py` (stub → real), `src/main.py` (register middleware)
- **Deps:** none (structlog already in use from P0)
- **APIs:** all HTTP responses gain `X-Request-ID`; no new routes
- **AGENT.md:** no new packages; no body logging (PII); exceptions re-raised after error log
- **Docs:** update `docs/context.md` after validation (Next step → 1.9)
- **Non-goals:** rate limit middleware (1.10), TripEditEvent (1.9), pytest middleware header asserts (deferred from 1.11 until after 1.8/1.10), auth changes, new env vars
