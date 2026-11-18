"""Slice 6 canonical trip: status, provenance, version. Flag off stays legacy."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.config import get_settings
from src.core.middleware.rate_limit import InMemoryRateLimiter, _reset_rate_limiter_for_tests
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.places.models import Place
from src.travel_engine.findings import make_finding
from src.trips.models import GeometryProvenance, StopStatus, Trip, TripPlace, TripStatus
from src.trips.schemas import TripOut
from src.trips.service import TripService
from tests.snapshots.seed import encode_polyline
from tests.travel_engine.fake_routing import FakeRoutingProvider
from tests.trips.test_edit_replan import _count_edit_events, _seed_owned_trip
from tests.trips.test_save_from_state import _complete_state, _seed_dest_and_places


@pytest.fixture
def memory_limiter():
    _reset_rate_limiter_for_tests(InMemoryRateLimiter())
    yield
    _reset_rate_limiter_for_tests(None)


@pytest.fixture
def canonical_on(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "CANONICAL_TRIP_V2_ENABLED", True)
    monkeypatch.setattr(settings, "CANONICAL_TRIP_MAX_SUGGESTIONS_PER_DAY", 3)
    monkeypatch.setattr(settings, "ROUTING_BACKEND", "haversine")
    return settings


def _line() -> str:
    return encode_polyline([(27.041, 88.263), (27.042, 88.264)])


@pytest.mark.asyncio
async def test_flag_off_json_omits_canonical_keys(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    saved = await TripService(db_session).save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id="sess-off",
    )
    assert saved is not None
    trip = await TripService(db_session).repo.get_with_places(saved.id)
    assert trip is not None
    payload = TripOut.from_trip(trip).model_dump(mode="json")
    assert "version" not in payload
    assert "stop_status" not in payload["places"][0]
    assert "geometry_provenance" not in payload["places"][0]


@pytest.mark.asyncio
async def test_flag_on_save_stores_dropped_stop_as_suggested(
    db_session, canonical_on
) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=2)
    state = _complete_state(dest.id, places[:1])
    state["route"] = [
        {
            "day": 1,
            "dropped_stops": [
                {"place_id": str(places[1].id), "name": places[1].name, "reason": "budget"},
                {"place_id": str(places[0].id), "name": "routed", "reason": "budget"},
            ],
        }
    ]
    trip = await TripService(db_session).save_from_state(
        state, user_id=None, session_id="sess-sug"
    )
    assert trip is not None
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    by_place = {row.place_id: row for row in loaded.places}
    assert by_place[places[0].id].stop_status == StopStatus.CONFIRMED
    assert by_place[places[1].id].stop_status == StopStatus.SUGGESTED
    assert by_place[places[1].id].order_in_day == 0
    assert by_place[places[1].id].polyline is None
    body = TripService(db_session).build_geojson(loaded)
    point_ids = [
        feature["properties"]["place_id"]
        for feature in body["features"]
        if feature["geometry"]["type"] == "Point"
    ]
    assert str(places[1].id) not in point_ids
    assert str(places[0].id) in point_ids


@pytest.mark.asyncio
async def test_flag_off_save_writes_no_suggestion(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=2)
    state = _complete_state(dest.id, places[:1])
    state["route"] = [
        {"dropped_stops": [{"place_id": str(places[1].id), "reason": "budget"}]}
    ]
    trip = await TripService(db_session).save_from_state(
        state, user_id=None, session_id="sess-nosug"
    )
    assert trip is not None
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    assert len(loaded.places) == 1


@pytest.mark.asyncio
async def test_haversine_null_polyline_is_not_a_road(db_session, canonical_on) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    state = _complete_state(dest.id, places)
    state["schedule"][0]["stops"][0]["leg_polyline"] = None
    trip = await TripService(db_session).save_from_state(
        state, user_id=None, session_id="sess-hav"
    )
    assert trip is not None
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    assert loaded.places[0].geometry_provenance == GeometryProvenance.HAVERSINE_ESTIMATE
    body = TripService(db_session).build_geojson(loaded)
    assert all(feature["geometry"]["type"] == "Point" for feature in body["features"])


@pytest.mark.asyncio
async def test_osrm_line_is_labeled_and_mixed_day_has_no_line(
    db_session, canonical_on
) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    rows = sorted(trip.places, key=lambda row: row.order_in_day)
    rows[0].polyline = _line()
    rows[0].geometry_provenance = GeometryProvenance.OSRM
    rows[1].polyline = _line()
    rows[1].geometry_provenance = GeometryProvenance.NONE
    await db_session.commit()
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    body = TripService(db_session).build_geojson(loaded)
    assert not any(feature["geometry"]["type"] == "LineString" for feature in body["features"])

    for row in loaded.places:
        row.geometry_provenance = GeometryProvenance.OSRM
        row.polyline = _line()
    await db_session.commit()
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    body = TripService(db_session).build_geojson(loaded)
    lines = [feature for feature in body["features"] if feature["geometry"]["type"] == "LineString"]
    assert len(lines) == 1
    assert lines[0]["properties"]["geometry_provenance"] == "osrm"
    assert user is not None
    assert places


@pytest.mark.asyncio
async def test_add_promotes_suggestion_and_remove_keeps_row(
    db_session, canonical_on
) -> None:
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    extra = Place(
        osm_id=f"node/sug-{uuid.uuid4().hex[:8]}",
        name="Suggested",
        category="attraction",
        tags={},
        enriched_tags=[],
        location=from_shape(Point(88.28, 27.05), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(extra)
    await db_session.flush()
    db_session.add(
        TripPlace(
            trip_id=trip.id,
            place_id=extra.id,
            day_number=1,
            order_in_day=0,
            stop_status=StopStatus.SUGGESTED,
            geometry_provenance=GeometryProvenance.NONE,
        )
    )
    await db_session.commit()
    db_session.expire(trip, ["places"])
    routing = FakeRoutingProvider()
    svc = TripService(db_session, routing=routing)
    promoted = await svc.add_stop(trip.id, 1, extra.id, user.id, expected_version=1)
    match = next(row for row in promoted.places if row.place_id == extra.id)
    assert match.stop_status == StopStatus.USER_ADDED
    assert match.order_in_day >= 1
    assert promoted.version == 2

    removed = await TripService(db_session, routing=routing).remove_stop(
        trip.id, 1, extra.id, user.id, expected_version=2
    )
    kept = next(row for row in removed.places if row.place_id == extra.id)
    assert kept.stop_status == StopStatus.REMOVED
    body = TripService(db_session).build_geojson(removed)
    assert str(extra.id) not in {
        feature["properties"].get("place_id")
        for feature in body["features"]
        if feature["geometry"]["type"] == "Point"
    }


@pytest.mark.asyncio
async def test_flag_off_remove_hard_deletes(db_session) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    routing = FakeRoutingProvider()
    updated = await TripService(db_session, routing=routing).remove_stop(
        trip.id, 1, places[0].id, user.id
    )
    assert all(row.place_id != places[0].id for row in updated.places)
    assert updated.version == 1


@pytest.mark.asyncio
async def test_blocking_finding_leaves_trip_unchanged(
    db_session, canonical_on, monkeypatch
) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    before_order = [row.place_id for row in sorted(trip.places, key=lambda row: row.order_in_day)]

    def _blocked(*_args, **_kwargs):
        return [
            make_finding(
                "INVALID_COORDINATES",
                day=1,
                stop_ids=[places[0].id],
                message="bad",
            )
        ]

    monkeypatch.setattr("src.trips.service.collect_findings", _blocked)
    with pytest.raises(Exception) as caught:
        await TripService(db_session, routing=FakeRoutingProvider()).reorder_stops(
            trip.id,
            1,
            [places[1].id, places[0].id],
            user.id,
            expected_version=1,
        )
    assert caught.value.status_code == 422
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    assert [row.place_id for row in sorted(loaded.places, key=lambda row: row.order_in_day)] == before_order
    assert loaded.version == 1
    assert await _count_edit_events(db_session, trip.id) == 0


@pytest.mark.asyncio
async def test_version_match_mismatch_and_legacy(
    client, db_session, canonical_on, memory_limiter, monkeypatch
) -> None:
    fake = FakeRoutingProvider()

    class _Patched(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _Patched)
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}
    path = f"/api/v1/trips/{trip.id}/days/1/stops/reorder"
    order = [str(places[1].id), str(places[0].id)]

    stale = await client.patch(
        path,
        headers={**headers, "If-Match": '"9"'},
        json={"place_ids": order},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "trip_version_conflict"
    assert await _count_edit_events(db_session, trip.id) == 0

    fresh = await client.get(f"/api/v1/trips/{trip.id}", headers=headers)
    assert fresh.status_code == 200
    assert fresh.json()["data"]["version"] == 1
    assert fresh.headers["etag"] == '"1"'

    ok = await client.patch(
        path,
        headers={**headers, "If-Match": '"1"'},
        json={"place_ids": order},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["version"] == 2
    assert ok.headers["etag"] == '"2"'

    legacy = await client.post(
        f"/api/v1/trips/{trip.id}/days/1/reoptimize",
        headers=headers,
    )
    assert legacy.status_code == 200
    assert legacy.json()["data"]["version"] == 3


@pytest.mark.asyncio
async def test_flag_off_ignores_stale_if_match(
    client, db_session, memory_limiter, monkeypatch
) -> None:
    fake = FakeRoutingProvider()

    class _Patched(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _Patched)
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    token = create_access_token(user.id, user.email)
    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        headers={
            "Authorization": f"Bearer {token}",
            "If-Match": '"99"',
        },
        json={"place_ids": [str(places[1].id), str(places[0].id)]},
    )
    assert response.status_code == 200
    assert "version" not in response.json()["data"]
    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    assert loaded.version == 1
