## 1. Middleware implementation

- [x] 1.1 Replace stub `src/core/middleware/logging.py` with `RequestLoggingMiddleware` per step 1.8 (generate/propagate `X-Request-ID`, clear+bind structlog contextvars, `request.start` / `request.end` / `request.error`, re-raise exceptions, no body logging)

## 2. App wiring

- [x] 2.1 Register `RequestLoggingMiddleware` in `create_app()` via `app.add_middleware` (after app creation, before routers) so it is outermost

## 3. Validation

- [x] 3.1 Start uvicorn and confirm `GET /api/v1/health` response includes `X-Request-ID`
- [x] 3.2 Confirm custom `X-Request-ID: my-trace-id-42` is echoed unchanged
- [x] 3.3 Confirm server logs show `request.start` and `request.end` with the same `request_id`, plus `latency_ms` on end

## 4. Context checkpoint

- [x] 4.1 Update `docs/context.md` — mark 1.8 done, Next step **1.9**, add middleware to Implemented modules, remove it from stubs-only list
