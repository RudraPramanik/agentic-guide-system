"""P7.3 trips edit HTTP — OpenAPI, auth, rate limit, thin would-drop."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.auth.models import User
from src.core.middleware.rate_limit import _reset_rate_limiter_for_tests
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.places.models import Place
from src.travel_engine.travel_rules import MAX_DAILY_TRAVEL_MIN
from src.trips.models import Trip, TripPlace, TripStatus
from src.trips.service import TripService
from tests.travel_engine.fake_routing import FakeRoutingProvider

_EDIT_PATHS = (
    "/api/v1/trips/{trip_id}/days/{day}/stops/reorder",
    "/api/v1/trips/{trip_id}/days/{day}/stops/{place_id}",
    "/api/v1/trips/{trip_id}/days/{day}/stops",
    "/api/v1/trips/{trip_id}/days/{day}/reoptimize",
)


class _TripEditKeyedLimiter:
    """
    Deny only after ``allow_count`` checks on ``*:trip_edit`` keys.

    Middleware shares ``get_rate_limiter()`` and uses ``ip:path`` keys — those
    MUST always pass so this test isolates the user-keyed dependency.
    """

    def __init__(self, allow_count: int) -> None:
        self.allow_count = allow_count
        self.edit_calls = 0

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        if not key.endswith(":trip_edit"):
            return True, limit
        self.edit_calls += 1
        if self.edit_calls <= self.allow_count:
            return True, max(0, self.allow_count - self.edit_calls)
        return False, 0


@pytest.fixture
def use_fake_routing(monkeypatch):
    """Force TripService constructed by the router to use FakeRoutingProvider."""
    fake = FakeRoutingProvider()

    class _PatchedTripService(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _PatchedTripService)
    return fake


async def _seed_owned_trip_http(
    db_session,
    *,
    n_places: int = 3,
) -> tuple[User, Destination, list[Place], Trip]:
    user = User(
        email=f"edit-http-{uuid.uuid4().hex[:8]}@example.com",
        name="Editor",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    dest = Destination(
        name="Edit HTTP City",
        country="IN",
        display_name="Edit HTTP City",
        osm_place_id=f"relation/edithttp-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    places: list[Place] = []
    for i in range(n_places):
        place = Place(
            osm_id=f"node/edithttp-{uuid.uuid4().hex[:8]}",
            name=f"Stop {i}",
            category="attraction",
            tags={},
            enriched_tags=[],
            location=from_shape(Point(88.263 + i * 0.01, 27.041), srid=4326),
            destination_id=dest.id,
        )
        db_session.add(place)
        places.append(place)
    await db_session.flush()

    trip = Trip(
        user_id=user.id,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        destination_id=dest.id,
        days=1,
        preferences={"base_lat": 27.041, "base_lng": 88.263, "interests": []},
        status=TripStatus.COMPLETE,
    )
    db_session.add(trip)
    await db_session.flush()

    for i, place in enumerate(places):
        db_session.add(
            TripPlace(
                trip_id=trip.id,
                place_id=place.id,
                day_number=1,
                order_in_day=i + 1,
                travel_time_min=10,
                visit_duration_min=60,
                suggested_start_time=f"{8 + i:02d}:00",
                polyline=f"old_poly_{i}",
            )
        )
    await db_session.commit()
    return user, dest, places, trip


@pytest.mark.asyncio
async def test_openapi_lists_four_edit_routes(client) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in _EDIT_PATHS:
        assert path in paths, f"missing OpenAPI path {path}"


@pytest.mark.asyncio
async def test_owner_reorder_returns_trip_out(client, db_session, use_fake_routing) -> None:
    user, _dest, places, trip = await _seed_owned_trip_http(db_session, n_places=3)
    token = create_access_token(user.id, user.email)
    new_order = [str(places[2].id), str(places[1].id), str(places[0].id)]

    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        headers={"Authorization": f"Bearer {token}"},
        json={"place_ids": new_order},
    )
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    day1 = [p for p in body["data"]["places"] if p["day_number"] == 1]
    day1_sorted = sorted(day1, key=lambda p: p["order_in_day"])
    assert [p["place_id"] for p in day1_sorted] == new_order


@pytest.mark.asyncio
async def test_guest_edit_returns_401(client, db_session) -> None:
    _user, _dest, places, trip = await _seed_owned_trip_http(db_session, n_places=2)
    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        json={"place_ids": [str(places[1].id), str(places[0].id)]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_owner_edit_returns_403(client, db_session, use_fake_routing) -> None:
    _owner, _dest, places, trip = await _seed_owned_trip_http(db_session, n_places=2)
    other = User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()
    token = create_access_token(other.id, other.email)

    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        headers={"Authorization": f"Bearer {token}"},
        json={"place_ids": [str(places[1].id), str(places[0].id)]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_trip_edit_rate_limit_21st_returns_429(
    client, db_session, use_fake_routing, monkeypatch
) -> None:
    user, _dest, places, trip = await _seed_owned_trip_http(db_session, n_places=2)
    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"place_ids": [str(places[1].id), str(places[0].id)]}
    url = f"/api/v1/trips/{trip.id}/days/1/stops/reorder"

    limiter = _TripEditKeyedLimiter(allow_count=20)
    _reset_rate_limiter_for_tests(limiter)
    try:
        for i in range(20):
            # Alternate permutations so each call is a valid reorder
            order = body["place_ids"] if i % 2 == 0 else list(reversed(body["place_ids"]))
            resp = await client.patch(url, headers=headers, json={"place_ids": order})
            assert resp.status_code == 200, f"call {i + 1}: {resp.status_code} {resp.text}"

        denied = await client.patch(url, headers=headers, json=body)
        assert denied.status_code == 429
        assert denied.json()["code"] == "rate_limit_exceeded"

        # Trip still has two stops (unchanged by denied call)
        get_resp = await client.get(
            f"/api/v1/trips/{trip.id}",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert len(get_resp.json()["data"]["places"]) == 2
    finally:
        _reset_rate_limiter_for_tests(None)


@pytest.mark.asyncio
async def test_add_would_drop_returns_422_trip_unchanged(
    client, db_session, monkeypatch
) -> None:
    user, dest, places, trip = await _seed_owned_trip_http(db_session, n_places=2)
    extra = Place(
        osm_id=f"node/edithttp-extra-{uuid.uuid4().hex[:8]}",
        name="Extra Dropper",
        category="attraction",
        tags={},
        enriched_tags=[],
        location=from_shape(Point(88.30, 27.05), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(extra)
    await db_session.commit()

    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)

    class _PatchedTripService(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _PatchedTripService)

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    before = await client.get(f"/api/v1/trips/{trip.id}", headers=headers)
    assert before.status_code == 200
    before_places = before.json()["data"]["places"]

    response = await client.post(
        f"/api/v1/trips/{trip.id}/days/1/stops",
        headers=headers,
        json={"place_id": str(extra.id)},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "edit_would_drop_other_stops"

    after = await client.get(f"/api/v1/trips/{trip.id}", headers=headers)
    assert after.status_code == 200
    assert after.json()["data"]["places"] == before_places
