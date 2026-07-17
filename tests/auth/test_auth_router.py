"""API / feature tests for auth router."""

from __future__ import annotations

import pytest

from src.auth.repository import UserRepository
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
    r = await client.get("/api/v1/auth/google")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "not configured" in data["data"]["message"].lower()


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
