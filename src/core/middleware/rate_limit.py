"""Rate limit middleware — InMemory / Redis backends, fail-open on errors."""

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

_REDIS_RL_PREFIX = "wandr:rl:"


class RateLimiterBackend(Protocol):
    """InMemory (dev) or RedisRateLimiter when REDIS_URL is set."""

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]: ...


class InMemoryRateLimiter:
    """
    Sliding window rate limiter backed by in-memory dict.
    Safe for single-process async use. NOT shared across workers.
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

            stale_keys = [k for k, timestamps in self._windows.items() if not timestamps]
            for stale_key in stale_keys:
                del self._windows[stale_key]

            count = len(self._windows[key])
            if count >= limit:
                return False, 0

            self._windows[key].append(now)
            return True, limit - count - 1


class RedisRateLimiter:
    """
    Sliding-window limiter using a Redis ZSET of request timestamps.
    Raises on Redis errors so middleware fail-open can catch them.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window
        redis_key = f"{_REDIS_RL_PREFIX}{key}"
        pipe = self._client.pipeline()  # type: ignore[attr-defined]
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        results = await pipe.execute()
        count = int(results[1])
        if count >= limit:
            return False, 0

        member = f"{now}:{id(asyncio.current_task())}"
        pipe2 = self._client.pipeline()  # type: ignore[attr-defined]
        pipe2.zadd(redis_key, {member: now})
        pipe2.expire(redis_key, max(int(window) + 1, 1))
        await pipe2.execute()
        return True, limit - count - 1


_limiter: RateLimiterBackend | None = None


def _build_redis_client():
    from redis.asyncio import Redis

    settings = get_settings()
    return Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        decode_responses=True,
    )


def get_rate_limiter() -> RateLimiterBackend:
    """Return the process-wide rate limiter (InMemory if REDIS_URL empty)."""
    global _limiter
    if _limiter is not None:
        return _limiter

    settings = get_settings()
    if settings.REDIS_URL:
        _limiter = RedisRateLimiter(_build_redis_client())
    else:
        _limiter = InMemoryRateLimiter()
    return _limiter


def _reset_rate_limiter_for_tests(backend: RateLimiterBackend | None = None) -> None:
    """Test helper — force a backend or clear so next get_rate_limiter() rebuilds."""
    global _limiter
    _limiter = backend


def _route_limit_table() -> list[tuple[str, int, int]]:
    """
    Ordered (path, limit, window) table, most specific first. Built from settings so
    nothing is hardcoded outside get_settings() (AGENT.md rule).
    """
    settings = get_settings()
    return [
        (
            settings.RATE_LIMIT_PLANNER_PATH,
            settings.RATE_LIMIT_PLANNER_REQUESTS,
            settings.RATE_LIMIT_PLANNER_WINDOW_SECONDS,
        ),
        (
            settings.RATE_LIMIT_DESTINATIONS_SEARCH_PATH,
            settings.RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS,
            settings.RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS,
        ),
    ]


def _resolve_limits(path: str) -> tuple[int, int]:
    """
    Exact-match lookup against the route table; falls back to the global default
    (RATE_LIMIT_DEFAULT_REQUESTS / _WINDOW_SECONDS) if no specific rule matches.
    """
    for route_path, limit, window in _route_limit_table():
        if path == route_path:
            return limit, window
    settings = get_settings()
    return settings.RATE_LIMIT_DEFAULT_REQUESTS, settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS


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
            # Fail open — never block users because of a limiter bug / Redis down
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
