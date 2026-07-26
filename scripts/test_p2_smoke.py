"""
P2 smoke test — run: python scripts/test_p2_smoke.py

Hits real Nominatim + Overpass + OSRM (network required). Uses the development
database and commits seed data. ASCII [OK]/[FAIL] markers for Windows.
Fail-fast: first failed section exits non-zero.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow `python scripts/test_p2_smoke.py` without requiring PYTHONPATH.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from httpx import ASGITransport, AsyncClient

from scripts.seed_destination import seed_places
from src.core.database.session import AsyncSessionLocal, dispose_engine
from src.core.observability.logging import configure_logging
from src.destinations.models import Destination
from src.destinations.repository import DestinationRepository
from src.geo.geocoder import _clear_cache_for_tests, cache_stats, geocode
from src.geo.osrm import get_route
from src.geo.overpass import fetch_pois
from src.geo.schemas import RawPOI
from src.main import create_app
from src.places.repository import PlaceRepository

DESTINATION = "Darjeeling"
RADIUS_KM = 30.0
VOLUME_FLOOR = 50
READINESS_FLOOR = 100


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(section: str, msg: str) -> None:
    print(f"  [FAIL] {section}: {msg}")
    raise AssertionError(f"{section}: {msg}")


async def section_geocoder():
    print("\n--- 1. Geocoder + cache ---")
    _clear_cache_for_tests()
    first = await geocode(DESTINATION)
    if first is None:
        _fail("Geocoder", "geocode(Darjeeling) returned None")
    hits_before = cache_stats()["hits"]
    second = await geocode(DESTINATION)
    if second is None:
        _fail("Geocoder", "second geocode returned None")
    if cache_stats()["hits"] <= hits_before:
        _fail("Geocoder", f"expected cache hit; stats={cache_stats()}")
    _ok(f"geocoded {first.name} lat={first.lat:.3f} lng={first.lng:.3f}; cache hit confirmed")
    return first


async def section_overpass(lat: float, lng: float) -> list[RawPOI]:
    print("\n--- 2. Overpass volume ---")
    pois = await fetch_pois(lat, lng, RADIUS_KM)
    if len(pois) < VOLUME_FLOOR:
        _fail("Overpass", f"expected >= {VOLUME_FLOOR} POIs, got {len(pois)}")
    _ok(f"fetched {len(pois)} POIs")
    return pois


async def section_seed(geocoded, pois: list[RawPOI]) -> Destination:
    print("\n--- 3/4. Seed + DB volume ---")
    async with AsyncSessionLocal() as session:
        dest_repo = DestinationRepository(session)
        place_repo = PlaceRepository(session)
        dest = await dest_repo.upsert_from_geocoded(geocoded)
        success = await seed_places(session, dest.id, pois)
        # Denormalized counter must reflect unique places in DB (re-seeds can return
        # a smaller Overpass subset than a prior run left behind).
        actual = await place_repo.count_by_destination(dest.id)
        dest = await dest_repo.update(dest.id, {"place_count": actual})
        await session.commit()
        await session.refresh(dest)
        if dest.place_count < VOLUME_FLOOR:
            _fail(
                "DB",
                f"place_count={dest.place_count} below volume floor {VOLUME_FLOOR}",
            )
        _ok(
            f"seeded id={dest.id} upserted={success}/{len(pois)} "
            f"place_count={dest.place_count}"
        )
        session.expunge(dest)
        return dest


async def section_idempotency(dest: Destination, pois: list[RawPOI]) -> None:
    print("\n--- 4b. Seed idempotency (reuse fetched POIs) ---")
    async with AsyncSessionLocal() as session:
        place_repo = PlaceRepository(session)
        before = await place_repo.count_by_destination(dest.id)
        await seed_places(session, dest.id, pois)
        await session.commit()
        after = await place_repo.count_by_destination(dest.id)
        if after != before:
            _fail("Idempotency", f"place count changed {before} -> {after}")
        _ok(f"reapplied {len(pois)} POIs; unique count stable at {after}")


async def section_http(dest: Destination) -> None:
    print("\n--- 5/6/7. HTTP search, places, readiness, rate-limit ---")
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        search = await client.get(f"/api/v1/destinations/search?q={DESTINATION}")
        if search.status_code != 200:
            _fail("HTTP search", f"status={search.status_code} body={search.text}")
        limit_header = search.headers.get("x-ratelimit-limit")
        if limit_header != "20":
            _fail("Rate limit", f"expected x-ratelimit-limit=20, got {limit_header!r}")
        _ok("search 200 with x-ratelimit-limit: 20")

        places = await client.get(
            f"/api/v1/places?destination_id={dest.id}&page=2&size=10"
        )
        if places.status_code != 200:
            _fail("HTTP places", f"status={places.status_code} body={places.text}")
        places_body = places.json()
        if places_body.get("total", 0) < VOLUME_FLOOR:
            _fail("HTTP places", f"total={places_body.get('total')} below volume floor")
        if not places_body.get("has_next"):
            _fail("HTTP places", "expected has_next=true on page=2 size=10")
        _ok(
            f"places page2 size10 total={places_body['total']} "
            f"items={len(places_body.get('items', []))}"
        )

        readiness = await client.get(f"/api/v1/destinations/{dest.id}/readiness")
        if readiness.status_code != 200:
            _fail(
                "HTTP readiness",
                f"status={readiness.status_code} body={readiness.text}",
            )
        data = readiness.json()["data"]
        if dest.place_count < READINESS_FLOOR:
            _fail(
                "Readiness",
                f"place_count={dest.place_count} < {READINESS_FLOOR}; "
                "cannot claim limited-band from volume floor alone",
            )
        if data.get("tier") != "limited":
            _fail("Readiness", f"tier={data.get('tier')!r}, expected limited")
        score = float(data["score"])
        if not (0.35 <= score <= 0.45):
            _fail("Readiness", f"score={score} not in [0.35, 0.45]")
        _ok(f"readiness tier=limited score={score} place_count={data['place_count']}")


async def section_osrm() -> None:
    print("\n--- 8. OSRM route or fallback ---")
    result = await get_route([(27.04, 88.26), (27.03, 88.27)])
    if result.distance_km <= 0:
        _fail("OSRM", f"distance_km={result.distance_km}")
    _ok(
        f"route distance_km={result.distance_km:.3f} "
        f"fallback_used={result.fallback_used}"
    )


async def section_radius(dest: Destination, pois: list[RawPOI]) -> None:
    print("\n--- 9. Geography radius sanity ---")
    async with AsyncSessionLocal() as session:
        refreshed = await DestinationRepository(session).get_by_id(dest.id)
        assert refreshed is not None
        limit = max(refreshed.place_count, len(pois), 100)
        found = await PlaceRepository(session).find_within_radius(
            refreshed.lat,
            refreshed.lng,
            RADIUS_KM,
            limit=limit,
        )
        found_osm = {p.osm_id for p in found}
        missing = [poi.osm_id for poi in pois if poi.osm_id not in found_osm]
        if missing:
            _fail(
                "Radius",
                f"{len(missing)} just-fetched POIs missing within {RADIUS_KM}km "
                f"(e.g. {missing[:3]}); found={len(found)} place_count={refreshed.place_count}",
            )
        if len(found) < VOLUME_FLOOR:
            _fail(
                "Radius",
                f"found only {len(found)} within {RADIUS_KM}km; expected >= {VOLUME_FLOOR}",
            )
        _ok(
            f"all {len(pois)} fetched POIs found within {RADIUS_KM}km "
            f"(query returned {len(found)})"
        )


async def main() -> int:
    configure_logging()
    try:
        geocoded = await section_geocoder()
        pois = await section_overpass(geocoded.lat, geocoded.lng)
        dest = await section_seed(geocoded, pois)
        await section_idempotency(dest, pois)
        await section_http(dest)
        await section_osrm()
        await section_radius(dest, pois)
    except AssertionError:
        return 1
    except Exception as exc:  # noqa: BLE001 — smoke must never look like a silent pass
        print(f"  [FAIL] Unexpected: {type(exc).__name__}: {exc}")
        return 1
    finally:
        await dispose_engine()

    print("\nALL P2 SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
