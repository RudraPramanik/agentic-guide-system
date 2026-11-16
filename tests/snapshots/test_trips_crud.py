"""Frozen trip list, get, delete, and claim, including guest versus owner."""

from __future__ import annotations

import pytest

from src.auth.router import COOKIE_SESSION
from tests.snapshots.compare import assert_fixture
from tests.snapshots.seed import GUEST_SESSION, seed_owner, seed_saved_trip


@pytest.mark.asyncio
async def test_list_without_credentials_matches_fixture(client) -> None:
    response = await client.get("/api/v1/trips")

    assert response.status_code == 401
    body = response.json()
    assert "data" not in body or body.get("success") is False
    assert_fixture("unauthorized.json", body)


@pytest.mark.asyncio
async def test_guest_get_matching_session_matches_fixture(client, db_session) -> None:
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        osm_prefix="guest-get",
    )

    response = await client.get(
        f"/api/v1/trips/{trip.id}",
        cookies={COOKIE_SESSION: GUEST_SESSION},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert_fixture("guest-get.json", response.json())


@pytest.mark.asyncio
async def test_guest_get_mismatched_session_is_403(client, db_session) -> None:
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        osm_prefix="guest-miss",
    )

    response = await client.get(
        f"/api/v1/trips/{trip.id}",
        cookies={COOKIE_SESSION: "snapshot-other-session"},
    )

    assert response.status_code == 403
    assert response.status_code != 404
    assert_fixture("guest-forbidden.json", response.json())


@pytest.mark.asyncio
async def test_delete_without_credentials_matches_fixture(client, db_session) -> None:
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        osm_prefix="guest-delete",
    )

    response = await client.delete(f"/api/v1/trips/{trip.id}")

    assert response.status_code == 401
    assert_fixture("unauthorized.json", response.json())


@pytest.mark.asyncio
async def test_claim_matching_session_matches_fixture(client, db_session) -> None:
    user, token = await seed_owner(
        db_session,
        email="snapshot-claim@wandr.dev",
        google_id="g-snapshot-claim",
    )
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        osm_prefix="guest-claim",
    )

    response = await client.post(
        f"/api/v1/trips/{trip.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
        cookies={COOKIE_SESSION: GUEST_SESSION},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == str(user.id)
    assert_fixture("claim.json", response.json())
