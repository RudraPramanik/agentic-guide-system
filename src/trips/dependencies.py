"""Trip-specific FastAPI dependencies (P7.3)."""

from __future__ import annotations

from fastapi import Depends

from src.config import get_settings
from src.core.exceptions import RateLimitedError
from src.core.middleware.rate_limit import get_rate_limiter
from src.core.security.jwt import TokenPayload
from src.core.security.permissions import require_auth


async def rate_limit_trip_edit(
    payload: TokenPayload = Depends(require_auth),
) -> TokenPayload:
    """
    User-keyed trip-edit rate limit.

    Key is ``{user_id}:trip_edit`` — do NOT add UUID edit paths to
    ``_route_limit_table``. Middleware IP/path default may still apply
    (dual limit is OK).
    """
    settings = get_settings()
    limiter = get_rate_limiter()
    key = f"{payload.user_id}:trip_edit"
    try:
        allowed, _ = await limiter.is_allowed(
            key,
            settings.RATE_LIMIT_TRIP_EDIT_REQUESTS,
            settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS,
        )
    except Exception:
        return payload  # fail open — never block edits because Redis/limiter is down
    if not allowed:
        raise RateLimitedError(
            message=(
                f"Too many requests. Retry after "
                f"{settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS} seconds."
            ),
            details={
                "retry_after_seconds": settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS,
                "limit": settings.RATE_LIMIT_TRIP_EDIT_REQUESTS,
            },
        )
    return payload
