"""
P1 database smoke test — run against the dev database after completing all P1 steps.
Not a pytest test. Run directly: python scripts/test_p1_smoke.py
All DB writes are rolled back at the end. No permanent data is written.
"""

from __future__ import annotations

import asyncio
import uuid

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.repository import UserRepository
from src.core.database.session import AsyncSessionLocal, get_engine
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.models import EditType, Trip, TripEditEvent, TripStatus

EXPECTED_TABLES = [
    "users",
    "destinations",
    "places",
    "trips",
    "trip_places",
    "trip_evaluations",
    "trip_edit_events",
]


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    raise AssertionError(msg)


async def test_connection() -> None:
    print("\n--- 1. Connection + Pool ---")
    engine = get_engine()
    async with engine.connect() as conn:
        ver = (await conn.execute(text("SELECT version()"))).scalar()
        _ok(f"Connected: {ver[:55]}...")
        db = (await conn.execute(text("SELECT current_database()"))).scalar()
        _ok(f"Database: {db}")


async def test_all_tables_exist() -> None:
    print("\n--- 2. All 7 Tables Exist ---")
    engine = get_engine()
    async with engine.connect() as conn:
        for table in EXPECTED_TABLES:
            exists = (
                await conn.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_name=:table)"
                    ),
                    {"table": table},
                )
            ).scalar()
            if exists:
                _ok(table)
            else:
                _fail(f"Table '{table}' missing — run: alembic upgrade head")


async def test_postgis_geometry() -> None:
    print("\n--- 3. PostGIS Geometry Insert + Read ---")
    async with AsyncSessionLocal() as session:
        dest = Destination(
            name="Smoke Test City",
            country="Testland",
            display_name="Smoke Test City, Testland",
            lat=27.041,
            lng=88.263,
        )
        session.add(dest)
        await session.flush()
        _ok(f"Destination inserted: id={dest.id}")

        place = Place(
            osm_id=f"smoke_{uuid.uuid4().hex[:12]}",
            name="Tiger Hill (Smoke Test)",
            category="viewpoint",
            destination_id=dest.id,
            location=from_shape(Point(88.263, 27.041), srid=4326),
        )
        session.add(place)
        await session.flush()
        _ok(f"Place with PostGIS geometry inserted: id={place.id}")

        fetched = (
            await session.execute(select(Place).where(Place.id == place.id))
        ).scalar_one()
        assert fetched.name == "Tiger Hill (Smoke Test)"
        _ok(f"Place read back: name={fetched.name}, category={fetched.category}")

        nearby = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM places "
                    "WHERE ST_DWithin(location::geography, "
                    "ST_MakePoint(:lng, :lat)::geography, :radius)"
                ),
                {"lng": 88.263, "lat": 27.041, "radius": 1000},
            )
        ).scalar()
        assert nearby >= 1
        _ok(f"ST_DWithin radius query returned {nearby} result(s)")

        await session.rollback()
        _ok("Rolled back — no permanent data written")


async def test_soft_delete_filter() -> None:
    print("\n--- 4. Soft Delete Filter ---")
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.create(
            {
                "email": f"smoke_{uuid.uuid4().hex[:8]}@wandr.dev",
                "name": "Smoke Test User",
                "is_active": True,
            }
        )
        uid = user.id
        await repo.soft_delete(uid)

        raw = (
            await session.execute(select(User).where(User.id == uid))
        ).scalar_one_or_none()
        assert raw is not None, "Raw query should find soft-deleted user"
        assert raw.deleted_at is not None

        filtered = (
            await session.execute(
                select(User).where(User.id == uid, User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        assert filtered is None, "Filtered query must NOT return soft-deleted user"
        assert await repo.get_by_id(uid) is None

        _ok("Soft delete filter works correctly")
        await session.rollback()


async def test_migration_state() -> None:
    print("\n--- 5. Migration State ---")
    engine = get_engine()
    async with engine.connect() as conn:
        rev = (
            await conn.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar()
        assert rev is not None, "No migrations applied — run: alembic upgrade head"
        _ok(f"Current alembic revision: {rev}")


async def test_trip_edit_event_cascade(session: AsyncSession) -> None:
    """Insert TripEditEvent; verify CASCADE when trip is deleted."""
    dest = Destination(
        name="Edit Event City",
        country="Testland",
        display_name="Edit Event City, Testland",
        lat=27.0,
        lng=88.0,
    )
    session.add(dest)
    await session.flush()

    place = Place(
        osm_id=f"edit_{uuid.uuid4().hex[:12]}",
        name="Edit Test Place",
        category="viewpoint",
        destination_id=dest.id,
        location=from_shape(Point(88.0, 27.0), srid=4326),
    )
    session.add(place)
    await session.flush()

    trip = Trip(
        session_id=f"smoke-{uuid.uuid4().hex[:8]}",
        destination_id=dest.id,
        days=1,
        preferences={},
        status=TripStatus.DRAFT,
    )
    session.add(trip)
    await session.flush()

    edit_event = TripEditEvent(
        trip_id=trip.id,
        edit_type=EditType.REORDER,
        day_number=1,
        place_id=place.id,
        payload={"from": 2, "to": 1},
    )
    session.add(edit_event)
    await session.flush()
    event_id = edit_event.id
    _ok(f"TripEditEvent inserted: id={event_id}")

    found = (
        await session.execute(
            select(TripEditEvent).where(TripEditEvent.id == event_id)
        )
    ).scalar_one_or_none()
    assert found is not None
    _ok("TripEditEvent read back OK")

    await session.delete(trip)
    await session.flush()

    after_cascade = (
        await session.execute(
            select(TripEditEvent).where(TripEditEvent.id == event_id)
        )
    ).scalar_one_or_none()
    assert after_cascade is None, "Trip delete must CASCADE to trip_edit_events"
    _ok("Trip CASCADE removed TripEditEvent")


async def test_trip_edit_events() -> None:
    print("\n--- 6. TripEditEvent + CASCADE ---")
    async with AsyncSessionLocal() as session:
        await test_trip_edit_event_cascade(session)
        await session.rollback()
        _ok("Rolled back — no permanent data written")


async def main() -> None:
    print("=" * 52)
    print("  Wandr P1 — Database Smoke Test")
    print("=" * 52)
    try:
        await test_connection()
        await test_all_tables_exist()
        await test_postgis_geometry()
        await test_soft_delete_filter()
        await test_migration_state()
        await test_trip_edit_events()

        print("\n" + "=" * 52)
        print("  ALL P1 SMOKE TESTS PASSED")
        print("  Ready to start P2.")
        print("=" * 52 + "\n")
    except AssertionError as e:
        print(f"\n[FAIL] SMOKE TEST FAILED: {e}")
        raise SystemExit(1) from e
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        raise SystemExit(1) from e


if __name__ == "__main__":
    asyncio.run(main())
