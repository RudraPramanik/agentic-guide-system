"""Wandr — async database engine and connection pool."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.config import get_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
        )
    return _engine


async def ping_db() -> None:
    """Verify database connectivity with a lightweight query."""

    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    """Dispose the connection pool on application shutdown."""

    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
