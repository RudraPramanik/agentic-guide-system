"""Shared Overpass place ingest — CLI seed and HTTP prepare both call this.

Geo only via ``src.geo``. No httpx, no LLM. Caller owns the session commit.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.observability.logging import get_logger
from src.destinations.models import Destination
from src.destinations.repository import DestinationRepository
from src.geo.geocoder import geocode
from src.geo.overpass import fetch_pois
from src.geo.schemas import GeocodedPlace, RawPOI
from src.places.repository import PlaceRepository

DEFAULT_RADIUS_KM = 30.0
PROGRESS_EVERY = 10

log = get_logger(__name__)


async def seed_places(
    session: AsyncSession,
    destination_id: uuid.UUID,
    pois: list[RawPOI],
) -> int:
    """Upsert each POI, skipping failures. Returns the success count.

    Each upsert runs in its own SAVEPOINT so one bad row cannot abort the
    surrounding transaction and take the rest of the batch with it.
    """
    repo = PlaceRepository(session)
    total = len(pois)
    success = 0

    for index, poi in enumerate(pois, start=1):
        try:
            async with session.begin_nested():
                await repo.upsert_from_poi(poi, destination_id)
        except Exception as exc:  # noqa: BLE001 — one bad POI must not abort the batch
            log.warning("seed.poi_failed", osm_id=poi.osm_id, error=str(exc))
            continue

        success += 1
        if index % PROGRESS_EVERY == 0:
            print(f"  ... {index}/{total} POIs processed ({success} upserted)")

    return success


async def ingest_destination_pois(
    session: AsyncSession,
    dest: Destination,
    radius_km: float,
) -> tuple[Destination, int, int]:
    """Fetch Overpass POIs around the stored point, upsert, update ``place_count``.

    Does not geocode and does not commit. Does not touch enrich/index counters.
    """
    dest_repo = DestinationRepository(session)
    pois = await fetch_pois(dest.lat, dest.lng, radius_km)
    if not pois:
        log.warning(
            "seed.no_pois",
            destination=dest.name,
            destination_id=str(dest.id),
            radius_km=radius_km,
        )
        print(
            f"WARNING: Overpass returned no POIs for {dest.name} "
            f"within {radius_km}km - saving destination with place_count=0"
        )

    success = await seed_places(session, dest.id, pois)
    dest = await dest_repo.update(dest.id, {"place_count": success})
    return dest, success, len(pois)


async def seed_from_geocoded(
    session: AsyncSession,
    geocoded: GeocodedPlace,
    radius_km: float,
) -> tuple[Destination, int, int]:
    dest_repo = DestinationRepository(session)
    dest = await dest_repo.upsert_from_geocoded(geocoded)
    return await ingest_destination_pois(session, dest, radius_km)


async def seed_destination_into(
    session: AsyncSession,
    destination_name: str,
    radius_km: float,
) -> tuple[Destination, int, int]:
    """Geocode → upsert → Overpass ingest on *session*. Caller commits.

    Raises ValueError when geocode returns None (maps to CLI exit 1).
    """
    geocoded = await geocode(destination_name)
    if geocoded is None:
        raise ValueError(f"Geocode failed for {destination_name!r}")

    return await seed_from_geocoded(session, geocoded, radius_km)
