"""CLI: python scripts/test_overpass.py <lat> <lng> <radius_km>"""

from __future__ import annotations

import asyncio
import sys

from src.geo.overpass import fetch_pois


async def main() -> None:
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 27.041
    lng = float(sys.argv[2]) if len(sys.argv) > 2 else 88.263
    radius_km = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0

    pois = await fetch_pois(lat, lng, radius_km)
    print(f"Fetched {len(pois)} POIs")
    for poi in pois[:3]:
        print(f"  - {poi.name} ({poi.category}, {poi.osm_id})")


if __name__ == "__main__":
    asyncio.run(main())
