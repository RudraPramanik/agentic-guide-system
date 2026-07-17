"""Request ID + latency middleware — outermost Chain-of-Responsibility link."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Chain-of-Responsibility link: outermost middleware layer.
    Responsibilities:
      1. Generate or propagate X-Request-ID
      2. Bind request context to structlog so all log lines in this request share request_id
      3. Log request.start and request.end with latency_ms
      4. Add X-Request-ID to response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Generate or preserve request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. Bind to structlog context for this request — flows into every log line
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        log = structlog.get_logger()
        start = time.perf_counter()
        log.info("request.start")

        # 3. Process request — re-raise exceptions after logging (never swallow)
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log.error("request.error", latency_ms=elapsed_ms, error=str(exc), exc_info=True)
            raise

        # 4. Log completion
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info("request.end", status_code=response.status_code, latency_ms=elapsed_ms)

        # 5. Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
