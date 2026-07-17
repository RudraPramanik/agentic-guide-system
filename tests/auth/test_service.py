"""Unit tests for AuthService — DB upsert + mocked Google HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.auth.exceptions import GoogleOAuthError
from src.auth.repository import UserRepository
from src.auth.service import AuthService
from src.core.exceptions import UnauthorizedError


@pytest.mark.asyncio
async def test_upsert_creates_new_user(db_session) -> None:
    svc = AuthService(db_session)
    user = await svc.upsert_google_user(
        google_id="g-new",
        email="new@wandr.dev",
        name="New User",
        avatar_url="https://example.com/a.png",
    )
    assert user.email == "new@wandr.dev"
    assert user.google_id == "g-new"
    found = await UserRepository(db_session).get_by_google_id("g-new")
    assert found is not None
    assert found.id == user.id


@pytest.mark.asyncio
async def test_upsert_links_existing_email(db_session) -> None:
    repo = UserRepository(db_session)
    existing = await repo.create(
        {
            "email": "link@wandr.dev",
            "name": "Link Me",
            "google_id": None,
            "avatar_url": None,
            "is_active": True,
        }
    )
    svc = AuthService(db_session)
    user = await svc.upsert_google_user(
        google_id="g-link",
        email="link@wandr.dev",
        name="Link Me",
        avatar_url="https://example.com/b.png",
    )
    assert user.id == existing.id
    assert user.google_id == "g-link"
    assert user.avatar_url == "https://example.com/b.png"


@pytest.mark.asyncio
async def test_verify_google_token_401() -> None:
    svc = AuthService(AsyncMock())
    response = MagicMock()
    response.status_code = 401

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.auth.service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(UnauthorizedError):
            await svc.verify_google_token("bad-token")


@pytest.mark.asyncio
async def test_verify_google_token_connection_error() -> None:
    svc = AuthService(AsyncMock())

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.auth.service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(GoogleOAuthError):
            await svc.verify_google_token("any-token")
