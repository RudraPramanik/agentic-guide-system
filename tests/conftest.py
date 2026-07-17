"""Shared pytest fixtures — async DB session + ASGI client."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.core.database.base import Base
from src.core.database.session import get_db
from src.main import create_app

# Register all models on Base.metadata before create_all
import src.auth.models  # noqa: F401
import src.destinations.models  # noqa: F401
import src.evaluation.models  # noqa: F401
import src.places.models  # noqa: F401
import src.trips.models  # noqa: F401


def _test_db_url() -> str:
    """Derive test DB URL by appending _test to the dev DB name."""
    url = get_settings().DATABASE_URL
    parts = url.rsplit("/", 1)
    return parts[0] + "/" + parts[1].split("?")[0] + "_test"


@pytest.fixture(scope="session")
async def test_engine():
    """Session-scoped engine. Creates all tables once, drops them after the session."""
    engine = create_async_engine(_test_db_url(), echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped session. Rolls back uncommitted work, then truncates
    so AuthService.commit() cannot leak rows between tests.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        if table_names:
            await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with get_db overridden to the test session."""
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_token() -> str:
    """Returns a valid JWT for a synthetic test user."""
    from src.core.security.jwt import create_access_token

    return create_access_token(uuid.uuid4(), "testuser@wandr.dev")


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Authorization headers for authenticated test requests."""
    return {"Authorization": f"Bearer {auth_token}"}
