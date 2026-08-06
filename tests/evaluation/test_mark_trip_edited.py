"""P7.5 — EvaluationService.mark_trip_edited flag-only (no TripEditEvent)."""

from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from sqlalchemy import func, select

from src.evaluation.models import TripEvaluation
from src.evaluation.repository import EvaluationRepository
from src.evaluation.service import EvaluationService
from src.trips.models import TripEditEvent
from src.trips.service import TripService
from tests.travel_engine.fake_routing import FakeRoutingProvider
from tests.trips.test_edit_replan import _count_edit_events, _seed_owned_trip


async def _seed_evaluation(
    db_session,
    *,
    trip_id: UUID,
    destination_id: UUID,
    user_edited: bool = False,
) -> TripEvaluation:
    repo = EvaluationRepository(db_session)
    row = await repo.create_generation(
        {
            "trip_id": trip_id,
            "destination_id": destination_id,
            "raw_input": "test trip",
            "parsed_preferences": {},
            "user_edited": user_edited,
        }
    )
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _count_edit_events_all(db_session) -> int:
    return (
        await db_session.execute(select(func.count()).select_from(TripEditEvent))
    ).scalar_one()


@pytest.mark.asyncio
async def test_mark_trip_edited_sets_user_edited_flag(db_session) -> None:
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    evaluation = await _seed_evaluation(
        db_session, trip_id=trip.id, destination_id=dest.id, user_edited=False
    )
    assert evaluation.user_edited is False

    await EvaluationService(db_session).mark_trip_edited(trip.id)
    await db_session.commit()
    await db_session.refresh(evaluation)
    assert evaluation.user_edited is True

    # Via TripService edit path as well (already flagged → still True)
    order = [places[2].id, places[0].id, places[1].id]
    await TripService(db_session, routing=FakeRoutingProvider()).reorder_stops(
        trip.id, 1, order, user.id
    )
    await db_session.refresh(evaluation)
    assert evaluation.user_edited is True


@pytest.mark.asyncio
async def test_edit_without_evaluation_still_audits(db_session) -> None:
    _user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    before = await _count_edit_events(db_session, trip.id)
    assert before == 0

    # No TripEvaluation row — mark alone must no-op
    await EvaluationService(db_session).mark_trip_edited(trip.id)
    await db_session.commit()

    order = [places[1].id, places[0].id, places[2].id]
    await TripService(db_session, routing=FakeRoutingProvider()).reorder_stops(
        trip.id, 1, order, _user.id
    )
    after = await _count_edit_events(db_session, trip.id)
    assert after == 1
    assert (
        await db_session.execute(
            select(func.count())
            .select_from(TripEvaluation)
            .where(TripEvaluation.trip_id == trip.id)
        )
    ).scalar_one() == 0


@pytest.mark.asyncio
async def test_mark_trip_edited_inserts_zero_edit_events(db_session) -> None:
    _user, dest, _places, trip = await _seed_owned_trip(db_session, n_places=2)
    await _seed_evaluation(
        db_session, trip_id=trip.id, destination_id=dest.id, user_edited=False
    )
    before = await _count_edit_events_all(db_session)

    await EvaluationService(db_session).mark_trip_edited(trip.id)
    await db_session.commit()

    after = await _count_edit_events_all(db_session)
    assert after == before
    assert await _count_edit_events(db_session, trip.id) == 0


@pytest.mark.asyncio
async def test_already_edited_evaluation_is_noop(db_session) -> None:
    _user, dest, _places, trip = await _seed_owned_trip(db_session, n_places=2)
    evaluation = await _seed_evaluation(
        db_session, trip_id=trip.id, destination_id=dest.id, user_edited=True
    )
    assert evaluation.user_edited is True

    await EvaluationService(db_session).mark_trip_edited(trip.id)
    await db_session.commit()
    await db_session.refresh(evaluation)
    assert evaluation.user_edited is True

    # Missing trip_id entirely — still no raise
    await EvaluationService(db_session).mark_trip_edited(uuid.uuid4())
    await db_session.commit()
