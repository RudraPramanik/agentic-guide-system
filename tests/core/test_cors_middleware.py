"""Focused CORS middleware checks (full suite expands in step 4.9).

These tests avoid the shared `client` fixture so they do not require Postgres.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.mark.asyncio
async def test_cors_allows_configured_origin() -> None:
    with (
        patch("src.main.ping_db", new_callable=AsyncMock),
        patch(
            "src.search.client.ensure_places_collection",
            new_callable=AsyncMock,
        ),
        patch(
            "src.search.embeddings.ensure_embedding_model_loaded",
            new_callable=AsyncMock,
        ),
        patch(
            "src.search.client.close_qdrant_client",
            new_callable=AsyncMock,
        ),
        patch("src.main.dispose_engine", new_callable=AsyncMock),
        patch("src.main.flush_tracer"),
    ):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/v1/health",
                headers={"Origin": "http://localhost:3000"},
            )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert r.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_settings_have_no_wildcard() -> None:
    from src.config import get_settings

    origins = get_settings().CORS_ALLOWED_ORIGINS
    assert isinstance(origins, list)
    assert "*" not in origins
