"""Wandr — async database engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory, creating it on first use."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


def AsyncSessionLocal() -> AsyncSession:
    """Callable factory — returns a new session context manager."""

    return get_session_factory()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — one async session per request."""

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ping_db() -> None:
    """Verify database connectivity with a lightweight query."""

    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    """Dispose the connection pool on application shutdown."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None
