"""In-memory rate limit middleware — fail-open on backend errors."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Protocol

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import get_settings
from src.core.responses import ErrorResponse

log = structlog.get_logger()


class RateLimiterBackend(Protocol):
    """Extension point for P6 RedisRateLimiter when REDIS_URL is set."""

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]: ...


class InMemoryRateLimiter:
    """
    Sliding window rate limiter backed by in-memory dict.
    Safe for single-process async use. NOT shared across workers.
    For multi-worker prod: replace with RedisRateLimiter (P6 via REDIS_URL).
    """

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Return (allowed, remaining_requests) for a sliding window."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - window
            self._windows[key] = [t for t in self._windows[key] if t > cutoff]

            # Drop stale keys to bound memory in long-running dev servers
            stale_keys = [k for k, timestamps in self._windows.items() if not timestamps]
            for stale_key in stale_keys:
                del self._windows[stale_key]

            count = len(self._windows[key])
            if count >= limit:
                return False, 0

            self._windows[key].append(now)
            return True, limit - count - 1


_limiter: RateLimiterBackend = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimiterBackend:
    """Return the process-wide rate limiter backend (swappable in tests / P6)."""
    return _limiter


def _resolve_limits(path: str) -> tuple[int, int]:
    settings = get_settings()
    if path.startswith(settings.RATE_LIMIT_PLANNER_PATH):
        return (
            settings.RATE_LIMIT_PLANNER_REQUESTS,
            settings.RATE_LIMIT_PLANNER_WINDOW_SECONDS,
        )
    return (
        settings.RATE_LIMIT_DEFAULT_REQUESTS,
        settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS,
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        limit, window = _resolve_limits(path)
        key = f"{_client_ip(request)}:{path}"

        try:
            allowed, remaining = await get_rate_limiter().is_allowed(key, limit, window)
        except Exception as exc:
            # Fail open — never block users because of a limiter bug
            log.warning("rate_limiter.error", error=str(exc))
            allowed, remaining = True, -1

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
                content=ErrorResponse(
                    code="rate_limit_exceeded",
                    message=f"Too many requests. Retry after {window} seconds.",
                ).model_dump(),
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        if remaining >= 0:
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
