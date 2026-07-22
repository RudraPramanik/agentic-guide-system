"""Place repository — atomic PostGIS upsert, geography radius, destination list/count."""

from __future__ import annotations

import uuid

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import insert

from src.core.database.base_repository import BaseRepository
from src.core.pagination import PageParams
from src.geo.schemas import RawPOI
from src.places.models import Place


class PlaceRepository(BaseRepository[Place, uuid.UUID]):

    async def upsert_from_poi(self, poi: RawPOI, destination_id: uuid.UUID) -> Place:
        """Atomic INSERT ... ON CONFLICT (osm_id) DO UPDATE ... RETURNING.

        Flush/execute only — no commit. Returns the RETURNING row directly
        (no separate SELECT by osm_id).
        """
        location = ST_SetSRID(ST_MakePoint(poi.lng, poi.lat), 4326)
        stmt = (
            insert(Place)
            .values(
                osm_id=poi.osm_id,
                name=poi.name,
                category=poi.category,
                tags=poi.raw_tags,
                location=location,
                destination_id=destination_id,
            )
            .on_conflict_do_update(
                index_elements=[Place.osm_id],
                set_=dict(
                    name=poi.name,
                    category=poi.category,
                    tags=poi.raw_tags,
                    location=location,
                    destination_id=destination_id,
                    updated_at=func.now(),
                ),
            )
            .returning(Place)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def find_within_radius(
        self, lat: float, lng: float, radius_km: float, *, limit: int = 100
    ) -> list[Place]:
        """Return non-deleted places within radius_km (geography / meters)."""
        stmt = (
            select(Place)
            .where(
                self._soft_delete_filter(),
                ST_DWithin(
                    cast(Place.location, Geography),
                    cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), Geography),
                    radius_km * 1000,
                ),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_destination(
        self, destination_id: uuid.UUID, params: PageParams
    ) -> tuple[list[Place], int]:
        """Paginated non-deleted places for a destination."""
        return await self.list_paginated(
            filters={"destination_id": destination_id},
            params=params,
        )

    async def count_by_destination(self, destination_id: uuid.UUID) -> int:
        """COUNT non-deleted places for destination — used by seed script."""
        stmt = select(func.count()).select_from(Place).where(
            Place.destination_id == destination_id,
            self._soft_delete_filter(),
        )
        return (await self.session.execute(stmt)).scalar_one()
