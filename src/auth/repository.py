"""User repository — soft-delete aware lookups."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.auth.models import User
from src.core.database.base_repository import BaseRepository


class UserRepository(BaseRepository[User, uuid.UUID]):

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        stmt = select(User).where(
            User.google_id == google_id,
            User.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
