"""Middleware integration tests — request ID and rate limiting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.middleware import rate_limit as rate_limit_module


@pytest.mark.asyncio
async def test_x_request_id_present(client) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert "x-request-id" in r.headers


@pytest.mark.asyncio
async def test_x_request_id_preserved(client) -> None:
    r = await client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "my-trace-id-42"},
    )
    assert r.headers.get("x-request-id") == "my-trace-id-42"


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers
    assert r.headers["x-ratelimit-limit"] == "60"


@pytest.mark.asyncio
async def test_rate_limit_fail_open(client, mocker) -> None:
    mock_backend = MagicMock()
    mock_backend.is_allowed = AsyncMock(side_effect=RuntimeError("limiter bug"))
    mocker.patch.object(rate_limit_module, "get_rate_limiter", return_value=mock_backend)

    r = await client.get("/api/v1/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_returns_429(client, mocker) -> None:
    mock_backend = MagicMock()
    mock_backend.is_allowed = AsyncMock(return_value=(False, 0))
    mocker.patch.object(rate_limit_module, "get_rate_limiter", return_value=mock_backend)

    r = await client.get("/api/v1/health")
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"
    assert r.headers.get("x-ratelimit-remaining") == "0"
    body = r.json()
    assert body["success"] is False
    assert body["code"] == "rate_limit_exceeded"
