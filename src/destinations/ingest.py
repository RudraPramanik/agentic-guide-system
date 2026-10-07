"""Shared place ingest — CLI seed and HTTP prepare both call this.

Geo only via ``src.geo``. No httpx, no LLM. Caller owns the session commit.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.observability.logging import get_logger
from src.destinations.models import Destination
from src.destinations.repository import DestinationRepository
from src.geo.country import countries_match, country_from_tags, normalize_country
from src.geo.geocoder import geocode
from src.geo.places import fetch_destination_pois
from src.geo.schemas import GeocodedPlace, RawPOI
from src.places.repository import PlaceRepository

DEFAULT_RADIUS_KM = 30.0
PROGRESS_EVERY = 10

log = get_logger(__name__)


def poi_allowed_for_destination(poi: RawPOI, destination_country: str) -> bool:
    """Exclude POIs whose tagged country conflicts with the destination country.

    Missing country tags are allowed (common on OSM) so catalogs stay usable;
    tagged mismatches (cross-border) are dropped. Accepted POIs are stamped
    with ``wandr:country`` during upsert.
    """
    dest_c = normalize_country(destination_country)
    if dest_c is None:
        return True
    poi_c = country_from_tags(poi.raw_tags)
    if poi_c is None:
        return True
    return countries_match(poi_c, dest_c)


def stamp_poi_country(poi: RawPOI, destination_country: str) -> RawPOI:
    """Copy POI with wandr:country set for later planner filtering."""
    dest_c = normalize_country(destination_country) or destination_country
    tags = dict(poi.raw_tags or {})
    tags["wandr:country"] = dest_c
    return poi.model_copy(update={"raw_tags": tags})


async def seed_places(
    session: AsyncSession,
    destination_id: uuid.UUID,
    pois: list[RawPOI],
    *,
    destination_country: str | None = None,
) -> int:
    """Upsert each POI, skipping failures and cross-border tagged POIs.

    Returns the success count. Each upsert runs in its own SAVEPOINT so one
    bad row cannot abort the surrounding transaction.
    """
    repo = PlaceRepository(session)
    total = len(pois)
    success = 0
    skipped_country = 0

    for index, poi in enumerate(pois, start=1):
        if destination_country and not poi_allowed_for_destination(poi, destination_country):
            skipped_country += 1
            log.info(
                "seed.poi_skipped_country",
                osm_id=poi.osm_id,
                destination_country=destination_country,
                poi_country=country_from_tags(poi.raw_tags),
            )
            continue

        to_upsert = (
            stamp_poi_country(poi, destination_country)
            if destination_country
            else poi
        )
        try:
            async with session.begin_nested():
                await repo.upsert_from_poi(to_upsert, destination_id)
        except Exception as exc:  # noqa: BLE001 — one bad POI must not abort the batch
            log.warning("seed.poi_failed", osm_id=poi.osm_id, error=str(exc))
            continue

        success += 1
        if index % PROGRESS_EVERY == 0:
            print(f"  ... {index}/{total} POIs processed ({success} upserted)")

    if skipped_country:
        log.info(
            "seed.country_filtered",
            destination_id=str(destination_id),
            skipped=skipped_country,
            upserted=success,
        )
    return success


async def ingest_destination_pois(
    session: AsyncSession,
    dest: Destination,
    radius_km: float,
) -> tuple[Destination, int, int]:
    """Fetch POIs via places facade, upsert, update ``place_count``.

    Does not geocode and does not commit. Does not touch enrich/index counters.
    Radius-only scrape (no country polygon). Cross-border tagged POIs excluded.
    """
    dest_repo = DestinationRepository(session)
    pois = await fetch_destination_pois(dest.lat, dest.lng, radius_km)
    if not pois:
        log.warning(
            "seed.no_pois",
            destination=dest.name,
            destination_id=str(dest.id),
            radius_km=radius_km,
        )
        print(
            f"WARNING: Places facade returned no POIs for {dest.name} "
            f"within {radius_km}km - saving destination with place_count=0"
        )

    success = await seed_places(
        session,
        dest.id,
        pois,
        destination_country=dest.country,
    )
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
    """Geocode → upsert → places-facade ingest on *session*. Caller commits.

    Raises ValueError when geocode returns None (maps to CLI exit 1).
    """
    geocoded = await geocode(destination_name)
    if geocoded is None:
        raise ValueError(f"Geocode failed for {destination_name!r}")

    return await seed_from_geocoded(session, geocoded, radius_km)
