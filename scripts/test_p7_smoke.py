"""
P7 smoke — run: python scripts/test_p7_smoke.py

Offline FakeRoutingProvider by default (no live OSRM/LLM).
Optional live OSRM: OPTIONAL_LIVE_OSRM=1 python scripts/test_p7_smoke.py

Fail-fast: first failed section exits non-zero. Never ambiguous PASS.
Requires Postgres (docker compose) — uses get_settings().DATABASE_URL.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.auth.models import User
from src.config import get_settings
from src.core.database.session import dispose_engine, get_session_factory
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.models import Trip, TripEditEvent, TripPlace, TripStatus
from src.trips.service import TripService
from tests.travel_engine.fake_routing import FakeRoutingProvider

get_settings.cache_clear()

_FORBIDDEN_IMPORT = re.compile(
    r"(^|\n)\s*(import\s+(litellm|langgraph|redis)|"
    r"from\s+(litellm|langgraph|redis)(\.| )|"
    r"import\s+.*PlannerService|"
    r"from\s+\S+\s+import\s+.*\bPlannerService\b|"
    r"from\s+\S+\s+import\s+.*\bexecute_tool\b|"
    r"import\s+.*\bexecute_tool\b)",
    re.MULTILINE,
)

_EDIT_MODULES = (
    "src/trips/service.py",
    "src/trips/router.py",
    "src/trips/dependencies.py",
    "src/trips/schemas.py",
    "src/trips/exceptions.py",
    "src/trips/polyline.py",
    "src/trips/repository.py",
)


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(section: str, msg: str) -> None:
    print(f"  [FAIL] {section}: {msg}")
    raise AssertionError(f"{section}: {msg}")


def _encode_polyline(coords: list[tuple[float, float]]) -> str:
    """Minimal encoder pairing with decode_polyline (for Fake GeoJSON proof)."""

    def _encode_signed(num: int) -> str:
        num = ~(num << 1) if num < 0 else (num << 1)
        chunks: list[str] = []
        while num >= 0x20:
            chunks.append(chr((0x20 | (num & 0x1F)) + 63))
            num >>= 5
        chunks.append(chr(num + 63))
        return "".join(chunks)

    result: list[str] = []
    prev_lat = 0
    prev_lng = 0
    for lat, lng in coords:
        ilat = int(round(lat * 1e5))
        ilng = int(round(lng * 1e5))
        result.append(_encode_signed(ilat - prev_lat))
        result.append(_encode_signed(ilng - prev_lng))
        prev_lat, prev_lng = ilat, ilng
    return "".join(result)


def _fake_with_decodable_polylines() -> FakeRoutingProvider:
    """Fake that returns Google-encoded polylines so GeoJSON LineStrings appear."""

    def _poly(waypoints: list[tuple[float, float]]) -> str | None:
        if len(waypoints) < 2:
            return None
        # waypoints are (lat, lng)
        return _encode_polyline([(lat, lng) for lat, lng in waypoints])

    return FakeRoutingProvider(polyline_for=_poly)


def section_import_guards() -> None:
    print("\n--- 1. Import guards (trips edit modules) ---")
    hits: list[str] = []
    for rel in _EDIT_MODULES:
        path = _ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            hits.append(rel)
    if hits:
        _fail("import guards", f"forbidden import in: {hits}")
    _ok("no litellm/langgraph/PlannerService/execute_tool/redis in trips edit modules")


async def section_reorder_edit_event_geojson() -> None:
    live = os.environ.get("OPTIONAL_LIVE_OSRM", "").strip() in ("1", "true", "True")
    mode = "live OsrmRoutingProvider" if live else "offline FakeRoutingProvider"
    print(f"\n--- 2. Owned trip reorder + TripEditEvent + GeoJSON ({mode}) ---")

    if live:
        from src.planner.routing_provider import OsrmRoutingProvider

        routing = OsrmRoutingProvider()
    else:
        routing = _fake_with_decodable_polylines()

    factory = get_session_factory()
    async with factory() as session:
        user = User(
            email=f"p7-smoke-{uuid.uuid4().hex[:8]}@example.com",
            name="P7 Smoke",
            google_id=f"g-p7-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        dest = Destination(
            name="P7 Smoke City",
            country="IN",
            display_name="P7 Smoke City",
            osm_place_id=f"relation/p7-smoke-{uuid.uuid4().hex[:8]}",
            lat=27.041,
            lng=88.263,
        )
        session.add(dest)
        await session.flush()

        places: list[Place] = []
        for i in range(3):
            place = Place(
                osm_id=f"node/p7-smoke-{uuid.uuid4().hex[:8]}",
                name=f"P7 Stop {i}",
                category="attraction",
                tags={},
                enriched_tags=[],
                location=from_shape(Point(88.263 + i * 0.01, 27.041), srid=4326),
                destination_id=dest.id,
            )
            session.add(place)
            places.append(place)
        await session.flush()

        trip = Trip(
            user_id=user.id,
            session_id=f"p7-smoke-{uuid.uuid4().hex[:8]}",
            destination_id=dest.id,
            days=1,
            preferences={"base_lat": 27.041, "base_lng": 88.263, "interests": []},
            status=TripStatus.COMPLETE,
        )
        session.add(trip)
        await session.flush()

        for order, place in enumerate(places, start=1):
            session.add(
                TripPlace(
                    trip_id=trip.id,
                    place_id=place.id,
                    day_number=1,
                    order_in_day=order,
                    travel_time_min=10,
                    visit_duration_min=60,
                    suggested_start_time=f"{8 + order - 1:02d}:00",
                    polyline=None,
                )
            )
        await session.commit()
        trip_id = trip.id
        user_id = user.id
        new_order = [places[2].id, places[1].id, places[0].id]
        _ok(f"seeded owned trip {trip_id} with 3 day-1 stops")

    async with factory() as session:
        svc = TripService(session, routing=routing)
        updated = await svc.reorder_stops(
            trip_id, 1, new_order, user_id, routing=routing
        )
        day_places = sorted(
            [tp for tp in updated.places if tp.day_number == 1],
            key=lambda tp: tp.order_in_day,
        )
        if [tp.place_id for tp in day_places] != new_order:
            _fail("reorder", f"order mismatch: {[tp.place_id for tp in day_places]}")
        _ok("reorder day 1 preserved user order")

        event_count = (
            await session.execute(
                select(func.count())
                .select_from(TripEditEvent)
                .where(TripEditEvent.trip_id == trip_id)
            )
        ).scalar_one()
        if event_count != 1:
            _fail("TripEditEvent", f"expected exactly 1, got {event_count}")
        _ok("exactly one TripEditEvent after reorder")

        # Reload for GeoJSON (eager places + Place)
        reloaded = await svc.repo.get_with_places(trip_id)
        if reloaded is None:
            _fail("geojson", "trip missing after reorder")
        geo = svc.build_geojson(reloaded)
        features = geo.get("features") or []
        types = {f.get("geometry", {}).get("type") for f in features}
        has_polyline = any(
            tp.polyline for tp in (reloaded.places or []) if tp.day_number == 1
        )
        if has_polyline and "LineString" not in types:
            _fail(
                "geojson",
                f"polylines present but no LineString; types={types}",
            )
        if has_polyline:
            _ok("GeoJSON includes LineString when polylines present")
        else:
            # Live OSRM may fail-soft to null polylines — still a valid 200 path.
            _ok("GeoJSON ok (no polylines on places; LineString not required)")

        # Soft-delete smoke trip to limit litter (best-effort; naive UTC for TIMESTAMP WITHOUT TZ).
        from datetime import datetime, timezone

        reloaded.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        _ok("soft-deleted smoke trip")


async def main() -> None:
    print("P7 smoke — Edit & Replan close-out")
    try:
        section_import_guards()
        await section_reorder_edit_event_geojson()
        print("\nAll P7 smoke sections PASS")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError:
        sys.exit(1)
    except Exception as exc:
        print(f"  [FAIL] unexpected: {exc}")
        sys.exit(1)
