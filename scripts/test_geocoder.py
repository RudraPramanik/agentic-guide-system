"""CLI: python scripts/test_geocoder.py "Darjeeling" """

from __future__ import annotations

import asyncio
import sys

from src.geo.geocoder import geocode


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "Darjeeling"
    result = await geocode(query)
    if result:
        print(
            f"GeocodedPlace(name={result.name!r}, lat={result.lat:.3f}, lng={result.lng:.3f})"
        )
    else:
        print("Geocode failed — returned None")


if __name__ == "__main__":
    asyncio.run(main())
