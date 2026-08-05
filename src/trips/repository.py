"""Trip repository — soft-delete aware list/get with eager places."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository
from src.core.pagination import PageParams
from src.trips.models import Trip, TripPlace


class TripRepository(BaseRepository[Trip, uuid.UUID]):

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        params: PageParams,
    ) -> tuple[list[Trip], int]:
        return await self.list_paginated(
            filters={"user_id": user_id},
            params=params,
            order_by_col=Trip.created_at,
            order_desc=True,
        )

    async def list_by_session(
        self,
        session_id: str,
        params: PageParams,
    ) -> tuple[list[Trip], int]:
        return await self.list_paginated(
            filters={"session_id": session_id},
            params=params,
            order_by_col=Trip.created_at,
            order_desc=True,
        )

    async def get_with_places(self, trip_id: uuid.UUID) -> Trip | None:
        """Return trip with TripPlace + Place eagerly loaded, or None if missing/soft-deleted."""
        stmt = (
            select(Trip)
            .where(Trip.id == trip_id, self._soft_delete_filter())
            .options(
                selectinload(Trip.places).selectinload(TripPlace.place),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_trip_places(self, rows: list[dict[str, Any]]) -> list[TripPlace]:
        """Insert TripPlace rows. Flushes but does NOT commit."""
        objs = [TripPlace(**row) for row in rows]
        self.session.add_all(objs)
        await self.session.flush()
        return objs
