"""Planner run persistence: uniqueness, defaults, and non-destructive FKs."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DataError, IntegrityError, StatementError

from src.auth.models import User
from src.destinations.models import Destination
from src.planner.runs.models import PlannerRun, RunStatus
from src.planner.runs.repository import PlannerRunRepository
from src.trips.models import Trip, TripStatus


def _run_data(**overrides: object) -> dict:
    data: dict = {
        "session_id": "sess-run",
        "idempotency_key": "key-1",
    }
    data.update(overrides)
    return data


async def _user(db_session) -> User:
    user = User(
        email=f"run-{uuid.uuid4().hex[:8]}@wandr.dev",
        name="Runner",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _trip(db_session) -> Trip:
    dest = Destination(
        name="Run City",
        country="IN",
        display_name="Run City",
        osm_place_id=f"relation/run-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()
    trip = Trip(
        session_id="sess-owner",
        destination_id=dest.id,
        days=1,
        preferences={},
        status=TripStatus.DRAFT,
    )
    db_session.add(trip)
    await db_session.flush()
    return trip


@pytest.mark.asyncio
async def test_insert_defaults_status_and_leaves_optional_fields_empty(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    row = await repo.create(_run_data())

    assert row.id is not None
    assert row.session_id == "sess-run"
    assert row.idempotency_key == "key-1"
    assert row.status == RunStatus.ACCEPTED
    assert row.status == "accepted"
    assert row.user_id is None
    assert row.trip_id is None
    assert row.input_hash is None
    assert row.failure_code is None
    assert row.workflow_version is None
    assert row.model_name is None
    assert row.provider is None
    assert row.fallback_reason is None
    assert row.created_at is not None
    assert row.updated_at is not None


@pytest.mark.asyncio
async def test_unknown_status_is_rejected(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    with pytest.raises((LookupError, StatementError, DataError)):
        await repo.create(_run_data(status="running"))


@pytest.mark.asyncio
async def test_same_session_and_key_is_rejected(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    first = await repo.create(_run_data())
    assert first.id is not None
    with pytest.raises(IntegrityError):
        await repo.create(_run_data())


@pytest.mark.asyncio
async def test_same_key_on_another_session_is_stored(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    first = await repo.create(_run_data(session_id="sess-a"))
    second = await repo.create(_run_data(session_id="sess-b"))
    assert first.id != second.id
    assert await repo.get_by_session_key("sess-a", "key-1") is not None
    assert await repo.get_by_session_key("sess-b", "key-1") is not None


@pytest.mark.asyncio
async def test_same_user_and_key_is_rejected_across_sessions(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    user = await _user(db_session)
    first = await repo.create(
        _run_data(session_id="sess-a", user_id=user.id),
    )
    assert first.id is not None
    with pytest.raises(IntegrityError):
        await repo.create(_run_data(session_id="sess-b", user_id=user.id))


@pytest.mark.asyncio
async def test_overlong_session_id_or_key_is_rejected(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    with pytest.raises((DataError, StatementError)):
        await repo.create(_run_data(session_id="s" * 65))
    await db_session.rollback()
    with pytest.raises((DataError, StatementError)):
        await repo.create(_run_data(idempotency_key="k" * 129))


@pytest.mark.asyncio
async def test_unknown_user_is_rejected(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    with pytest.raises(IntegrityError):
        await repo.create(_run_data(user_id=uuid.uuid4()))


@pytest.mark.asyncio
async def test_rollback_hides_the_row(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    row = await repo.create(_run_data(session_id="sess-rollback"))
    run_id = row.id
    await db_session.rollback()
    assert await repo.get_by_id(run_id) is None
    count = (
        await db_session.execute(select(PlannerRun).where(PlannerRun.id == run_id))
    ).scalar_one_or_none()
    assert count is None


@pytest.mark.asyncio
async def test_deleting_user_keeps_run_and_clears_user_id(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    user = await _user(db_session)
    row = await repo.create(_run_data(user_id=user.id))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.flush()
    await db_session.refresh(row)
    assert row.user_id is None
    assert await repo.get_by_id(row.id) is not None


@pytest.mark.asyncio
async def test_deleting_trip_keeps_run_and_clears_trip_id(db_session) -> None:
    repo = PlannerRunRepository(db_session)
    trip = await _trip(db_session)
    row = await repo.create(_run_data(trip_id=trip.id))
    await db_session.execute(delete(Trip).where(Trip.id == trip.id))
    await db_session.flush()
    await db_session.refresh(row)
    assert row.trip_id is None
    assert await repo.get_by_id(row.id) is not None
