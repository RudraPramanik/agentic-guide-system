"""FastAPI auth dependencies — Bearer header preferred, then wandr_token cookie."""

from __future__ import annotations

import uuid

from fastapi import Depends, Request

from src.core.exceptions import UnauthorizedError
from src.core.security.jwt import TokenPayload, verify_token

COOKIE_TOKEN_NAME = "wandr_token"


def _extract_token(request: Request) -> str | None:
    """Prefer Authorization: Bearer …; fall back to wandr_token cookie."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            return token
    cookie_token = request.cookies.get(COOKIE_TOKEN_NAME)
    if cookie_token:
        return cookie_token.strip() or None
    return None


async def require_auth(request: Request) -> TokenPayload:
    """
    FastAPI dependency for protected endpoints.
    Raises UnauthorizedError (401) if token missing or invalid.
    """
    token = _extract_token(request)
    if not token:
        raise UnauthorizedError("Authentication required")
    payload = verify_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")
    return payload


async def optional_auth(request: Request) -> TokenPayload | None:
    """
    FastAPI dependency for endpoints that work for both guests and authenticated users.
    Returns TokenPayload for authenticated users, None for guests. Never raises.
    """
    token = _extract_token(request)
    if not token:
        return None
    return verify_token(token)


async def get_current_user_id(
    payload: TokenPayload = Depends(require_auth),
) -> uuid.UUID:
    """Convenience dependency — returns just the user_id UUID."""
    return payload.user_id
