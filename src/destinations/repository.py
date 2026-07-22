"""Destination repository — atomic geocode upsert and name search."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from src.core.database.base_repository import BaseRepository
from src.destinations.models import Destination
from src.geo.schemas import GeocodedPlace


class DestinationRepository(BaseRepository[Destination, uuid.UUID]):

    async def get_by_osm_place_id(self, osm_place_id: str) -> Destination | None:
        stmt = select(Destination).where(Destination.osm_place_id == osm_place_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search_by_name(self, query: str, *, limit: int = 10) -> list[Destination]:
        """ILIKE on name OR display_name; order by place_count desc, then name."""
        q = query.strip()
        pattern = f"%{q}%"
        stmt = (
            select(Destination)
            .where(
                or_(
                    Destination.name.ilike(pattern),
                    Destination.display_name.ilike(pattern),
                )
            )
            .order_by(Destination.place_count.desc(), Destination.name.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_from_geocoded(self, geocoded: GeocodedPlace) -> Destination:
        """Atomic INSERT ... ON CONFLICT (osm_place_id) DO UPDATE ... RETURNING.

        ON CONFLICT SET updates only geocode-derived fields — never place_count /
        enriched_count / indexed_count (owned by seed/enrich/index scripts).

        Flush/execute only — no commit. Caller (service) commits.
        """
        stmt = (
            insert(Destination)
            .values(
                name=geocoded.name,
                country=geocoded.country,
                display_name=geocoded.display_name,
                osm_place_id=geocoded.osm_place_id,
                lat=geocoded.lat,
                lng=geocoded.lng,
                place_count=0,
                enriched_count=0,
                indexed_count=0,
            )
            .on_conflict_do_update(
                index_elements=[Destination.osm_place_id],
                set_=dict(
                    name=geocoded.name,
                    country=geocoded.country,
                    display_name=geocoded.display_name,
                    lat=geocoded.lat,
                    lng=geocoded.lng,
                    updated_at=func.now(),
                ),
            )
            .returning(Destination)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
