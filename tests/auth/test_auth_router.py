"""API / feature tests for auth router."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.auth.repository import UserRepository
from src.auth.service import AuthService
from src.config import get_settings
from src.core.security.jwt import create_access_token


@pytest.mark.asyncio
async def test_health(client) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_me_guest(client) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["is_guest"] is True
    assert data["data"]["user"] is None
    assert data["data"]["session_id"]
    assert "wandr_session" in r.headers.get("set-cookie", "").lower()


@pytest.mark.asyncio
async def test_auth_logout_no_auth(client) -> None:
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert r.json()["data"]["message"] == "Logged out"


@pytest.mark.asyncio
async def test_auth_google_not_configured(client) -> None:
    settings = get_settings()
    settings.GOOGLE_CLIENT_ID = ""
    with patch("src.auth.router.get_settings", return_value=settings):
        r = await client.get("/api/v1/auth/google", follow_redirects=False)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "not configured" in data["data"]["message"].lower()


@pytest.mark.asyncio
async def test_auth_google_redirects_when_configured(client) -> None:
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        pytest.skip("GOOGLE_CLIENT_ID not set in environment")
    r = await client.get("/api/v1/auth/google", follow_redirects=False)
    assert r.status_code == 307
    location = r.headers["location"]
    assert location.startswith("https://accounts.google.com/")
    assert "client_id=" in location


@pytest.mark.asyncio
async def test_auth_me_cookie_authenticated(client, db_session) -> None:
    user = await UserRepository(db_session).create(
        {
            "email": "authed@wandr.dev",
            "name": "Authed User",
            "google_id": "g-authed",
            "avatar_url": None,
            "is_active": True,
        }
    )
    token = create_access_token(user.id, user.email)
    r = await client.get("/api/v1/auth/me", cookies={"wandr_token": token})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["is_guest"] is False
    assert data["data"]["user"]["email"] == "authed@wandr.dev"
    assert data["data"]["user"]["id"] == str(user.id)


@pytest.mark.asyncio
async def test_no_password_register_route(client) -> None:
    r = await client.post("/api/v1/auth/register", json={})
    assert r.status_code == 404
    r2 = await client.post("/api/v1/auth/login", json={})
    assert r2.status_code == 404


def _settings_with_frontend(frontend_url: str = "http://localhost:3000"):
    settings = get_settings()
    settings.FRONTEND_URL = frontend_url
    return settings


@pytest.mark.asyncio
async def test_oauth_callback_error_redirects_to_frontend(client) -> None:
    with patch("src.auth.router.get_settings", return_value=_settings_with_frontend()):
        r = await client.get("/api/v1/auth/callback?error=access_denied", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "http://localhost:3000/auth/error?reason=access_denied"


@pytest.mark.asyncio
async def test_oauth_callback_missing_code_redirects_to_frontend(client) -> None:
    with patch("src.auth.router.get_settings", return_value=_settings_with_frontend()):
        r = await client.get("/api/v1/auth/callback", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "http://localhost:3000/auth/error?reason=oauth_failed"


@pytest.mark.asyncio
async def test_oauth_callback_success_redirects_with_token_cookie(
    client, db_session
) -> None:
    mock_user = await UserRepository(db_session).create(
        {
            "email": "oauth@wandr.dev",
            "name": "OAuth User",
            "google_id": "g-oauth",
            "avatar_url": None,
            "is_active": True,
        }
    )

    with (
        patch("src.auth.router.get_settings", return_value=_settings_with_frontend()),
        patch.object(
            AuthService,
            "exchange_code_for_token",
            new=AsyncMock(return_value="google-access"),
        ),
        patch.object(
            AuthService,
            "verify_google_token",
            new=AsyncMock(
                return_value={
                    "sub": "g-oauth",
                    "email": "oauth@wandr.dev",
                    "name": "OAuth User",
                }
            ),
        ),
        patch.object(
            AuthService,
            "upsert_google_user",
            new=AsyncMock(return_value=mock_user),
        ),
    ):
        r = await client.get(
            "/api/v1/auth/callback?code=valid-code",
            follow_redirects=False,
        )

    assert r.status_code == 302
    assert r.headers["location"] == "http://localhost:3000/auth/done"
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "wandr_token=" in set_cookie
    assert "httponly" in set_cookie


@pytest.mark.asyncio
async def test_oauth_callback_success_json_fallback_without_frontend_url(
    client, db_session
) -> None:
    settings = get_settings()
    settings.FRONTEND_URL = ""

    mock_user = await UserRepository(db_session).create(
        {
            "email": "fallback@wandr.dev",
            "name": "Fallback User",
            "google_id": "g-fallback",
            "avatar_url": None,
            "is_active": True,
        }
    )

    with (
        patch("src.auth.router.get_settings", return_value=settings),
        patch.object(
            AuthService,
            "exchange_code_for_token",
            new=AsyncMock(return_value="google-access"),
        ),
        patch.object(
            AuthService,
            "verify_google_token",
            new=AsyncMock(
                return_value={
                    "sub": "g-fallback",
                    "email": "fallback@wandr.dev",
                    "name": "Fallback User",
                }
            ),
        ),
        patch.object(
            AuthService,
            "upsert_google_user",
            new=AsyncMock(return_value=mock_user),
        ),
    ):
        r = await client.get(
            "/api/v1/auth/callback?code=valid-code",
            follow_redirects=False,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["access_token"]
    assert data["data"]["user"]["email"] == "fallback@wandr.dev"
    assert "wandr_token=" in r.headers.get("set-cookie", "").lower()


def test_cookie_samesite_production_vs_dev() -> None:
    from src.auth.router import _cookie_samesite, _cookie_secure

    prod = get_settings().model_copy(update={"ENVIRONMENT": "production"})
    with patch("src.auth.router.get_settings", return_value=prod):
        assert _cookie_samesite() == "none"
        assert _cookie_secure() is True

    local = get_settings().model_copy(update={"ENVIRONMENT": "development"})
    with patch("src.auth.router.get_settings", return_value=local):
        assert _cookie_samesite() == "lax"
        assert _cookie_secure() is False


@pytest.mark.asyncio
async def test_auth_me_session_cookie_samesite_lax_by_default(client) -> None:
    r = await client.get("/api/v1/auth/me")
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "wandr_session=" in set_cookie
    assert "samesite=lax" in set_cookie


@pytest.mark.asyncio
async def test_auth_me_session_cookie_samesite_none_in_production(client) -> None:
    prod = get_settings().model_copy(update={"ENVIRONMENT": "production"})
    with patch("src.auth.router.get_settings", return_value=prod):
        r = await client.get("/api/v1/auth/me")
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "wandr_session=" in set_cookie
    assert "samesite=none" in set_cookie
    assert "secure" in set_cookie


@pytest.mark.asyncio
async def test_logout_delete_cookie_matches_production_flags(client) -> None:
    prod = get_settings().model_copy(update={"ENVIRONMENT": "production"})
    with patch("src.auth.router.get_settings", return_value=prod):
        r = await client.post("/api/v1/auth/logout")
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "wandr_token=" in set_cookie
    assert "samesite=none" in set_cookie
    assert "secure" in set_cookie

