"""Alembic up/down for planner_runs against a scratch database."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import get_settings

_ROOT = Path(__file__).resolve().parents[3]
_SCRATCH_DB = "wandr_planner_runs_mig"
_PREVIOUS_HEAD = "a1b2c3d4e5f6"
_OLDER_TABLES = {
    "users",
    "destinations",
    "places",
    "trips",
    "trip_places",
    "trip_evaluations",
    "trip_edit_events",
}


def _scratch_url() -> str:
    if not _SCRATCH_DB.endswith("_planner_runs_mig"):
        raise RuntimeError("scratch database name must end with _planner_runs_mig")
    url = make_url(get_settings().DATABASE_URL).set(database=_SCRATCH_DB)
    rendered = url.render_as_string(hide_password=False)
    if rendered.endswith("/wandr") or rendered.endswith("/wandr_test"):
        raise RuntimeError("refusing to point Alembic at wandr or wandr_test")
    return rendered


def _alembic(*args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _scratch_url()
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} failed\n{completed.stdout}\n{completed.stderr}"
        )


async def _admin_execute(statement: str) -> None:
    engine = create_async_engine(
        get_settings().DATABASE_URL,
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def _recreate_scratch() -> None:
    await _admin_execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{_SCRATCH_DB}' AND pid <> pg_backend_pid()"
    )
    try:
        await _admin_execute(f'DROP DATABASE IF EXISTS "{_SCRATCH_DB}"')
        await _admin_execute(f'CREATE DATABASE "{_SCRATCH_DB}"')
    except Exception as exc:
        pytest.fail(
            "CREATE DATABASE failed for the scratch migration database. "
            "Not pointing Alembic at wandr or wandr_test. "
            f"{type(exc).__name__}: {exc}"
        )


async def _public_tables() -> set[str]:
    engine = create_async_engine(_scratch_url())
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return {row[0] for row in rows}
    finally:
        await engine.dispose()


@pytest.fixture
async def scratch_database() -> AsyncIterator[None]:
    await _recreate_scratch()
    try:
        yield
    finally:
        await _admin_execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{_SCRATCH_DB}' AND pid <> pg_backend_pid()"
        )
        await _admin_execute(f'DROP DATABASE IF EXISTS "{_SCRATCH_DB}"')


@pytest.mark.asyncio
async def test_upgrade_from_previous_head_and_downgrade(scratch_database) -> None:
    _alembic("upgrade", _PREVIOUS_HEAD)
    tables = await _public_tables()
    assert "planner_runs" not in tables
    assert _OLDER_TABLES <= tables

    _alembic("upgrade", "head")
    tables = await _public_tables()
    assert "planner_runs" in tables
    assert _OLDER_TABLES <= tables

    _alembic("downgrade", "-1")
    tables = await _public_tables()
    assert "planner_runs" not in tables
    assert _OLDER_TABLES <= tables

    _alembic("upgrade", "head")
    tables = await _public_tables()
    assert "planner_runs" in tables
    assert _OLDER_TABLES <= tables


@pytest.mark.asyncio
async def test_empty_database_upgrade_head_creates_planner_runs(scratch_database) -> None:
    _alembic("upgrade", "head")
    tables = await _public_tables()
    assert "planner_runs" in tables
    assert _OLDER_TABLES <= tables
