"""Run status machine and idempotent resolve."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.auth.models import User
from src.config import get_settings
from src.core.exceptions import ForbiddenError
from src.planner.runs.exceptions import RunTransitionError
from src.planner.runs.models import PlannerRun, RunStatus
from src.planner.runs.service import WORKFLOW_VERSION, PlannerRunService

pytestmark = pytest.mark.asyncio


async def _resolve(db, *, session_id: str, user_id=None, key: str = "key-1"):
    return await PlannerRunService(db).resolve(
        session_id=session_id,
        user_id=user_id,
        idempotency_key=key,
        input_hash="hash-1",
    )


async def test_validating_can_become_partial(db_session) -> None:
    run, created = await _resolve(db_session, session_id="sess-partial")
    assert created is True
    service = PlannerRunService(db_session)
    await service.transition(run, RunStatus.VALIDATING, None)
    await service.transition(run, RunStatus.PARTIAL, None)
    assert run.status is RunStatus.PARTIAL


async def test_terminal_status_rejects_planning(db_session) -> None:
    run, _ = await _resolve(db_session, session_id="sess-terminal")
    service = PlannerRunService(db_session)
    await service.transition(run, RunStatus.COMPLETED, None)
    with pytest.raises(RunTransitionError):
        await service.transition(run, RunStatus.PLANNING, None)
    assert run.status is RunStatus.COMPLETED


async def test_start_row_is_planning_with_model_fields(db_session) -> None:
    run, _ = await _resolve(db_session, session_id="sess-start")
    settings = get_settings()
    assert run.status is RunStatus.PLANNING
    assert run.workflow_version == WORKFLOW_VERSION
    assert run.model_name == settings.LLM_MODEL
    assert run.provider == settings.LLM_MODEL.split("/", 1)[0]
    assert run.fallback_reason is None
    assert run.input_hash == "hash-1"


async def test_second_resolve_returns_the_same_run(db_session) -> None:
    first, created = await _resolve(db_session, session_id="sess-same")
    second, again = await _resolve(db_session, session_id="sess-same")
    assert created is True
    assert again is False
    assert second.id == first.id
    rows = (await db_session.execute(select(PlannerRun))).scalars().all()
    assert len(rows) == 1


async def test_authenticated_caller_does_not_see_another_users_run(db_session) -> None:
    owner = User(email="owner@example.com", name="Owner", is_active=True)
    other = User(email="other@example.com", name="Other", is_active=True)
    db_session.add_all([owner, other])
    await db_session.flush()
    await _resolve(db_session, session_id="sess-owner", user_id=owner.id, key="shared")
    found, created = await _resolve(
        db_session, session_id="sess-other", user_id=other.id, key="shared"
    )
    assert created is True
    assert found.user_id == other.id


async def test_claim_sets_user_on_guest_row(db_session) -> None:
    user = User(email="claim@example.com", name="Claim", is_active=True)
    db_session.add(user)
    await db_session.flush()
    guest, _ = await _resolve(db_session, session_id="sess-claim", key="claim-key")
    claimed, created = await _resolve(
        db_session,
        session_id="sess-claim",
        user_id=user.id,
        key="claim-key",
    )
    assert created is False
    assert claimed.id == guest.id
    assert claimed.user_id == user.id


async def test_wrong_session_is_forbidden(db_session) -> None:
    run, _ = await _resolve(db_session, session_id="sess-owner")
    service = PlannerRunService(db_session)
    with pytest.raises(ForbiddenError):
        await service.assert_can_access(run, user_id=None, session_id="someone-else")


async def test_integrity_conflict_returns_the_winner(db_session) -> None:
    service = PlannerRunService(db_session)
    winner, created = await service.resolve(
        session_id="sess-race",
        user_id=None,
        idempotency_key="race-key",
        input_hash="hash-1",
    )
    assert created is True

    async def miss_once(*args, **kwargs):
        if not miss_once.used:
            miss_once.used = True
            return None
        return await PlannerRunService._find(service, *args, **kwargs)

    miss_once.used = False
    service._find = miss_once  # type: ignore[method-assign]
    found, created_again = await service.resolve(
        session_id="sess-race",
        user_id=None,
        idempotency_key="race-key",
        input_hash="hash-other",
    )
    assert created_again is False
    assert found.id == winner.id
    assert found.input_hash == "hash-1"
    assert uuid.UUID(str(found.id))
