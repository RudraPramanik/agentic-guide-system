"""Destination HTTP dependencies — IP-keyed prepare limiter (not path-table)."""

from __future__ import annotations

from fastapi import Request

from src.config import get_settings
from src.core.exceptions import RateLimitedError
from src.core.middleware.rate_limit import get_rate_limiter


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )


async def rate_limit_destinations_prepare(request: Request) -> None:
    """
    IP-keyed prepare rate limit.

    Key is ``{ip}:dest_prepare`` — do NOT add UUID prepare paths to
    ``_route_limit_table``. Middleware IP/path default may still apply
    (dual limit is OK). Fail-open if the limiter backend raises.
    """
    settings = get_settings()
    limiter = get_rate_limiter()
    key = f"{_client_ip(request)}:dest_prepare"
    try:
        allowed, _ = await limiter.is_allowed(
            key,
            settings.RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS,
            settings.RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS,
        )
    except Exception:
        return
    if not allowed:
        raise RateLimitedError(
            message=(
                f"Too many requests. Retry after "
                f"{settings.RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS} seconds."
            ),
            details={
                "retry_after_seconds": settings.RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS,
                "limit": settings.RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS,
            },
        )
