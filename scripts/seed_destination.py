"""
Seed a destination with POIs from Overpass.
Usage: python scripts/seed_destination.py --destination "Darjeeling" --radius 30
Re-runnable (upsert). Commits on success.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import AsyncSessionLocal, dispose_engine
from src.core.observability.logging import configure_logging, get_logger
from src.destinations.repository import DestinationRepository
from src.geo.geocoder import geocode
from src.geo.overpass import fetch_pois
from src.geo.schemas import RawPOI
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


async def seed_destination(destination_name: str, radius_km: float) -> int:
    """Run the full seed pipeline. Returns a process exit code."""
    geocoded = await geocode(destination_name)
    if geocoded is None:
        print(
            f"Geocode failed for {destination_name!r} - nothing seeded. "
            "Check the spelling or try a more specific query.",
            file=sys.stderr,
        )
        return 1

    async with AsyncSessionLocal() as session:
        dest_repo = DestinationRepository(session)
        dest = await dest_repo.upsert_from_geocoded(geocoded)
        dest_id = dest.id
        dest_name = dest.name

        pois = await fetch_pois(dest.lat, dest.lng, radius_km)
        if not pois:
            log.warning(
                "seed.no_pois",
                destination=dest_name,
                destination_id=str(dest_id),
                radius_km=radius_km,
            )
            print(
                f"WARNING: Overpass returned no POIs for {dest_name} "
                f"within {radius_km}km - saving destination with place_count=0"
            )

        success = await seed_places(session, dest_id, pois)
        await dest_repo.update(dest_id, {"place_count": success})
        await session.commit()

    print(f"Seeded {success}/{len(pois)} places for {dest_name} (id={dest_id})")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a destination with Overpass POIs.")
    parser.add_argument("--destination", required=True, help="Destination name to geocode")
    parser.add_argument(
        "--radius",
        type=float,
        default=DEFAULT_RADIUS_KM,
        help=f"POI search radius in km (default: {DEFAULT_RADIUS_KM:g})",
    )
    return parser.parse_args()


async def main() -> int:
    configure_logging()
    args = _parse_args()
    try:
        return await seed_destination(args.destination, args.radius)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
