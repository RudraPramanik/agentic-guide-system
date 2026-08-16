"""
Seed a destination with POIs from Overpass.
Usage: python scripts/seed_destination.py --destination "Darjeeling" --radius 30
Re-runnable (upsert). Commits on success.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.core.database.session import AsyncSessionLocal, dispose_engine
from src.core.observability.logging import configure_logging
from src.destinations.ingest import (
    DEFAULT_RADIUS_KM,
    seed_destination_into,
    seed_from_geocoded,
    seed_places,
)
from src.geo.geocoder import geocode

# Re-export for existing tests: ``from scripts.seed_destination import seed_places``
__all__ = [
    "DEFAULT_RADIUS_KM",
    "seed_destination",
    "seed_destination_into",
    "seed_from_geocoded",
    "seed_places",
]


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
        dest, success, poi_total = await seed_from_geocoded(
            session, geocoded, radius_km
        )
        await session.commit()

    print(f"Seeded {success}/{poi_total} places for {dest.name} (id={dest.id})")
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
