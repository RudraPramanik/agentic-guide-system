"""Unit tests for auth FastAPI dependencies."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from src.core.exceptions import UnauthorizedError
from src.core.security.jwt import create_access_token
from src.core.security.permissions import (
    COOKIE_TOKEN_NAME,
    _extract_token,
    optional_auth,
    require_auth,
)


def _request(*, authorization: str | None = None, cookie: str | None = None) -> MagicMock:
    req = MagicMock()
    headers: dict[str, str] = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    req.headers.get = lambda key, default=None: headers.get(key, default)
    cookies: dict[str, str] = {}
    if cookie is not None:
        cookies[COOKIE_TOKEN_NAME] = cookie
    req.cookies.get = lambda key, default=None: cookies.get(key, default)
    return req


def test_extract_prefers_bearer_over_cookie() -> None:
    uid = uuid.uuid4()
    bearer = create_access_token(uid, "bearer@wandr.dev")
    cookie = create_access_token(uuid.uuid4(), "cookie@wandr.dev")
    token = _extract_token(_request(authorization=f"Bearer {bearer}", cookie=cookie))
    assert token == bearer


def test_extract_falls_back_to_cookie() -> None:
    cookie = create_access_token(uuid.uuid4(), "cookie@wandr.dev")
    assert _extract_token(_request(cookie=cookie)) == cookie


@pytest.mark.asyncio
async def test_require_auth_missing_token() -> None:
    with pytest.raises(UnauthorizedError):
        await require_auth(_request())


@pytest.mark.asyncio
async def test_require_auth_invalid_token() -> None:
    with pytest.raises(UnauthorizedError):
        await require_auth(_request(authorization="Bearer not.valid"))


@pytest.mark.asyncio
async def test_optional_auth_guest() -> None:
    assert await optional_auth(_request()) is None


@pytest.mark.asyncio
async def test_optional_auth_cookie() -> None:
    uid = uuid.uuid4()
    token = create_access_token(uid, "cookie@wandr.dev")
    payload = await optional_auth(_request(cookie=token))
    assert payload is not None
    assert payload.user_id == uid


@pytest.mark.asyncio
async def test_optional_auth_invalid_returns_none() -> None:
    assert await optional_auth(_request(authorization="Bearer bad.token")) is None
