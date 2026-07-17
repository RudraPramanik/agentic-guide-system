"""Unit tests for UserRepository."""

from __future__ import annotations

import pytest

from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_get_by_email_and_google_id(db_session) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(
        {
            "email": "repo@wandr.dev",
            "name": "Repo User",
            "google_id": "google-repo-1",
            "avatar_url": None,
            "is_active": True,
        }
    )
    assert (await repo.get_by_email("repo@wandr.dev")).id == user.id
    assert (await repo.get_by_google_id("google-repo-1")).id == user.id
    assert await repo.get_by_email("missing@wandr.dev") is None


@pytest.mark.asyncio
async def test_soft_deleted_user_excluded(db_session) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(
        {
            "email": "deleted@wandr.dev",
            "name": "Gone",
            "google_id": "google-deleted",
            "avatar_url": None,
            "is_active": True,
        }
    )
    await repo.soft_delete(user.id)
    assert await repo.get_by_email("deleted@wandr.dev") is None
    assert await repo.get_by_google_id("google-deleted") is None
