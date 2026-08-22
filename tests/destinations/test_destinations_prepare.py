"""Public destination prepare HTTP + ingest kickoff tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.cache.backends import InMemoryCacheBackend, _reset_cache_backend_for_tests
from src.core.middleware.rate_limit import _reset_rate_limiter_for_tests, _route_limit_table
from src.destinations.ingest import ingest_destination_pois
from src.destinations.models import Destination
from src.geo.schemas import RawPOI
from src.planner.router import PlannerService


def _dest(**kwargs) -> Destination:
    defaults = dict(
        name="Prepare Town",
        country="IN",
        display_name="Prepare Town",
        osm_place_id=f"relation/prep-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=0,
    )
    defaults.update(kwargs)
    return Destination(**defaults)


def _poi(osm_id: str) -> RawPOI:
    return RawPOI(
        osm_id=osm_id,
        name=f"Place {osm_id}",
        lat=27.04,
        lng=88.26,
        category="attraction",
        raw_tags={},
    )


def _swallow_task(coro, *args, **kwargs):
    if hasattr(coro, "close"):
        coro.close()
    return MagicMock()


@pytest.fixture(autouse=True)
def _reset_limiters_and_cache():
    _reset_rate_limiter_for_tests(None)
    yield
    _reset_rate_limiter_for_tests(None)


@pytest.fixture
def prepare_cache():
    backend = InMemoryCacheBackend()
    _reset_cache_backend_for_tests(backend)
    yield backend
    _reset_cache_backend_for_tests(None)


@pytest.mark.asyncio
async def test_prepare_unknown_destination_404(client) -> None:
    response = await client.post(
        "/api/v1/destinations/00000000-0000-0000-0000-000000000001/prepare"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_prepare_already_at_floor_is_200_ready_without_overpass(
    client, db_session, prepare_cache, mocker
) -> None:
    dest = _dest(place_count=10)
    db_session.add(dest)
    await db_session.flush()

    fetch = mocker.patch(
        "src.destinations.ingest.fetch_destination_pois",
        new_callable=AsyncMock,
    )
    create = mocker.patch(
        "src.destinations.service.asyncio.create_task",
        side_effect=_swallow_task,
    )

    response = await client.post(f"/api/v1/destinations/{dest.id}/prepare")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ready"
    assert body["data"]["place_count"] == 10
    fetch.assert_not_called()
    create.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_below_floor_returns_202_and_schedules_ingest(
    client, db_session, prepare_cache, mocker
) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    create = mocker.patch(
        "src.destinations.service.asyncio.create_task",
        side_effect=_swallow_task,
    )
    fetch = mocker.patch(
        "src.destinations.ingest.fetch_destination_pois",
        new_callable=AsyncMock,
    )

    response = await client.post(f"/api/v1/destinations/{dest.id}/prepare")

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "preparing"
    assert data["place_count"] == 0
    assert create.call_count == 1
    fetch.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_concurrent_second_call_does_not_double_scrape(
    client, db_session, prepare_cache, mocker
) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    create = mocker.patch(
        "src.destinations.service.asyncio.create_task",
        side_effect=_swallow_task,
    )

    first = await client.post(f"/api/v1/destinations/{dest.id}/prepare")
    second = await client.post(f"/api/v1/destinations/{dest.id}/prepare")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["status"] == "preparing"
    assert second.json()["data"]["status"] == "preparing"
    assert create.call_count == 1


@pytest.mark.asyncio
async def test_prepare_rate_limit_returns_429(
    client, db_session, prepare_cache, mocker
) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    mock_backend = MagicMock()
    mock_backend.is_allowed = AsyncMock(return_value=(False, 0))
    mocker.patch(
        "src.destinations.dependencies.get_rate_limiter",
        return_value=mock_backend,
    )
    create = mocker.patch(
        "src.destinations.service.asyncio.create_task",
        side_effect=_swallow_task,
    )

    response = await client.post(f"/api/v1/destinations/{dest.id}/prepare")

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limit_exceeded"
    create.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_limiter_exception_fails_open(
    client, db_session, prepare_cache, mocker
) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    mock_backend = MagicMock()
    mock_backend.is_allowed = AsyncMock(side_effect=RuntimeError("limiter down"))
    mocker.patch(
        "src.destinations.dependencies.get_rate_limiter",
        return_value=mock_backend,
    )
    mocker.patch(
        "src.destinations.service.asyncio.create_task",
        side_effect=_swallow_task,
    )

    response = await client.post(f"/api/v1/destinations/{dest.id}/prepare")

    assert response.status_code == 202
    assert response.json()["data"]["status"] == "preparing"


@pytest.mark.asyncio
async def test_prepare_radius_over_max_is_422(client, db_session) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/destinations/{dest.id}/prepare",
        json={"radius_km": 51},
    )

    assert response.status_code == 422


def test_prepare_uuid_path_absent_from_route_limit_table() -> None:
    paths = [row[0] for row in _route_limit_table()]
    assert all("prepare" not in path for path in paths)


@pytest.mark.asyncio
async def test_ingest_destination_pois_updates_place_count(
    db_session, mocker
) -> None:
    dest = _dest(place_count=0)
    db_session.add(dest)
    await db_session.flush()

    mocker.patch(
        "src.destinations.ingest.fetch_destination_pois",
        new=AsyncMock(return_value=[_poi("node/1"), _poi("node/2")]),
    )
    geocode = mocker.patch(
        "src.destinations.ingest.geocode",
        new_callable=AsyncMock,
    )

    updated, success, total = await ingest_destination_pois(db_session, dest, 30.0)

    assert success == 2
    assert total == 2
    assert updated.place_count == 2
    geocode.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_then_generate_floor_until_places_exist(
    client, db_session, mocker
) -> None:
    """Mocked proof: empty dest 409s generate; after ingest floor is met (guest, no login)."""
    dest = _dest(name="Shimla Shell", place_count=0)
    db_session.add(dest)
    await db_session.flush()

    blocked = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": "3 days"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "destination_not_ready"

    pois = [_poi(f"node/{i}") for i in range(12)]
    mocker.patch(
        "src.destinations.ingest.fetch_destination_pois",
        new=AsyncMock(return_value=pois),
    )
    await ingest_destination_pois(db_session, dest, 30.0)
    await db_session.refresh(dest)
    assert dest.place_count >= 10

    async def _fake_generate(**kwargs):
        kwargs["on_event"]("itinerary_done", {"days": []})
        return {
            "destination_id": str(dest.id),
            "schedule": [],
            "plan_complete": False,
            "abort_triggered": False,
        }

    mocker.patch.object(PlannerService, "generate", new=AsyncMock(side_effect=_fake_generate))

    allowed = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": "3 days"},
    )
    assert allowed.status_code == 200
    assert "event: itinerary_done" in allowed.text
    assert "wandr_session" in allowed.cookies
