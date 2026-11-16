"""Frozen day edits for an owner, with injected routing and anonymous 401s."""

from __future__ import annotations

import uuid

import pytest

from src.trips.service import TripService
from tests.snapshots.compare import assert_fixture, load_request
from tests.snapshots.seed import seed_owner, seed_place, seed_saved_trip
from tests.travel_engine.fake_routing import FakeRoutingProvider

_NIL = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def use_fake_routing(monkeypatch):
    fake = FakeRoutingProvider()

    class _PatchedTripService(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _PatchedTripService)
    return fake


async def _owned_trip(db_session, *, n_places: int, prefix: str):
    user, token = await seed_owner(
        db_session,
        email=f"{prefix}@wandr.dev",
        google_id=f"g-{prefix}",
    )
    dest, places, trip = await seed_saved_trip(
        db_session,
        session_id="snapshot-owner-session",
        user_id=user.id,
        n_places=n_places,
        osm_prefix=prefix,
    )
    return user, token, dest, places, trip


@pytest.mark.asyncio
async def test_owner_reorder_matches_fixture(client, db_session, use_fake_routing) -> None:
    _user, token, _dest, places, trip = await _owned_trip(
        db_session, n_places=3, prefix="reorder"
    )
    load_request("reorder.json")
    new_order = [str(places[2].id), str(places[1].id), str(places[0].id)]

    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        headers={"Authorization": f"Bearer {token}"},
        json={"place_ids": new_order},
    )

    assert response.status_code == 200
    body = response.json()
    day = sorted(
        (place for place in body["data"]["places"] if place["day_number"] == 1),
        key=lambda place: place["order_in_day"],
    )
    assert [place["name"] for place in day] == ["Stop 2", "Stop 1", "Stop 0"]
    assert_fixture("reorder.json", body)


@pytest.mark.asyncio
async def test_owner_remove_matches_fixture(client, db_session, use_fake_routing) -> None:
    _user, token, _dest, places, trip = await _owned_trip(
        db_session, n_places=3, prefix="remove"
    )

    response = await client.delete(
        f"/api/v1/trips/{trip.id}/days/1/stops/{places[1].id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert_fixture("remove-stop.json", response.json())


@pytest.mark.asyncio
async def test_owner_add_matches_fixture(client, db_session, use_fake_routing) -> None:
    _user, token, dest, _places, trip = await _owned_trip(
        db_session, n_places=2, prefix="add"
    )
    extra = await seed_place(
        db_session,
        dest,
        name="Stop Extra",
        osm_id="node/add-extra",
        lng=88.28,
        lat=27.0,
    )
    load_request("add-stop.json")

    response = await client.post(
        f"/api/v1/trips/{trip.id}/days/1/stops",
        headers={"Authorization": f"Bearer {token}"},
        json={"place_id": str(extra.id)},
    )

    assert response.status_code == 200
    assert_fixture("add-stop.json", response.json())


@pytest.mark.asyncio
async def test_owner_reoptimize_matches_fixture(client, db_session, use_fake_routing) -> None:
    _user, token, _dest, _places, trip = await _owned_trip(
        db_session, n_places=3, prefix="reopt"
    )

    response = await client.post(
        f"/api/v1/trips/{trip.id}/days/1/reoptimize",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert_fixture("reoptimize.json", response.json())


@pytest.mark.asyncio
async def test_anonymous_edits_are_401(client, monkeypatch) -> None:
    calls = {"n": 0}

    class _CountingTripService(TripService):
        def __init__(self, session, routing=None):
            calls["n"] += 1
            super().__init__(session, routing=routing)

    monkeypatch.setattr("src.trips.router.TripService", _CountingTripService)
    trip_id = str(uuid.uuid4())
    headers_absent: dict[str, str] = {}
    cases = [
        client.patch(
            f"/api/v1/trips/{trip_id}/days/1/stops/reorder",
            headers=headers_absent,
            json={"place_ids": [_NIL, _NIL]},
        ),
        client.delete(
            f"/api/v1/trips/{trip_id}/days/1/stops/{_NIL}",
            headers=headers_absent,
        ),
        client.post(
            f"/api/v1/trips/{trip_id}/days/1/stops",
            headers=headers_absent,
            json={"place_id": _NIL},
        ),
        client.post(
            f"/api/v1/trips/{trip_id}/days/1/reoptimize",
            headers=headers_absent,
        ),
    ]
    for pending in cases:
        response = await pending
        assert response.status_code == 401
        assert_fixture("unauthorized.json", response.json())
    assert calls["n"] == 0
