"""Place service — list/get with mandatory destination existence check."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PageParams
from src.destinations.exceptions import DestinationNotFoundError
from src.destinations.repository import DestinationRepository
from src.places.repository import PlaceRepository
from src.places.schemas import PlaceOut


class PlaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PlaceRepository(session)
        self.dest_repo = DestinationRepository(session)

    async def list_by_destination(
        self, destination_id: uuid.UUID, params: PageParams
    ) -> tuple[list[PlaceOut], int]:
        """
        LOCKED (v2): destination existence check is MANDATORY, not optional.
        1. Verify destination exists — raises DestinationNotFoundError (404)
        2. places, total = await self.repo.list_by_destination(...)
        3. return [PlaceOut.from_place(p) for p in places], total
        """
        dest = await self.dest_repo.get_by_id(destination_id)
        if dest is None:
            raise DestinationNotFoundError(destination_id=str(destination_id))

        places, total = await self.repo.list_by_destination(destination_id, params)
        return [PlaceOut.from_place(p) for p in places], total

    async def get_by_id(self, place_id: uuid.UUID) -> PlaceOut:
        """get_by_id_or_raise on Place repo → PlaceOut.from_place."""
        place = await self.repo.get_by_id_or_raise(place_id)
        return PlaceOut.from_place(place)
