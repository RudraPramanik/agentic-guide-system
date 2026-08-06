"""Trip repository — soft-delete aware list/get with eager places."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository
from src.core.pagination import PageParams
from src.trips.models import EditType, Trip, TripEditEvent, TripPlace


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

    async def delete_trip_place(
        self,
        trip_id: uuid.UUID,
        place_id: uuid.UUID,
        day_number: int,
    ) -> bool:
        """Hard-delete one TripPlace. Flush-only. Returns True if a row was deleted."""
        stmt = delete(TripPlace).where(
            TripPlace.trip_id == trip_id,
            TripPlace.place_id == place_id,
            TripPlace.day_number == day_number,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount)

    async def delete_day_places(
        self,
        trip_id: uuid.UUID,
        day_number: int,
    ) -> int:
        """Hard-delete all TripPlaces for a day. Flush-only. Returns deleted count."""
        stmt = delete(TripPlace).where(
            TripPlace.trip_id == trip_id,
            TripPlace.day_number == day_number,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def insert_edit_event(
        self,
        *,
        trip_id: uuid.UUID,
        edit_type: EditType,
        day_number: int | None = None,
        place_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TripEditEvent:
        """Sole writer of TripEditEvent rows. Flushes but does NOT commit."""
        event = TripEditEvent(
            trip_id=trip_id,
            edit_type=edit_type,
            day_number=day_number,
            place_id=place_id,
            payload=payload or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event
