"""Code-owned planner run status. The only module that assigns ``PlannerRun.status``."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.planner.runs.exceptions import (
    RunForbiddenError,
    RunNotFoundError,
    RunTransitionError,
)
from src.planner.runs.models import TERMINAL_RUN_STATUSES, PlannerRun, RunStatus
from src.planner.runs.repository import PlannerRunRepository

WORKFLOW_VERSION = "planner-v6.1"

_LEGAL: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.ACCEPTED: frozenset(
        {
            RunStatus.PLANNING,
            RunStatus.RESOLVING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        }
    ),
    RunStatus.RESOLVING: frozenset(
        {
            RunStatus.RESEARCHING,
            RunStatus.PLANNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        }
    ),
    RunStatus.RESEARCHING: frozenset(
        {
            RunStatus.PLANNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        }
    ),
    RunStatus.PLANNING: frozenset(
        {
            RunStatus.VALIDATING,
            RunStatus.COMPLETED,
            RunStatus.DEGRADED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        }
    ),
    RunStatus.VALIDATING: frozenset(
        {
            RunStatus.COMPLETED,
            RunStatus.PARTIAL,
            RunStatus.DEGRADED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
        }
    ),
}


def _provider_from_model(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/", 1)[0]
    return model_name


class PlannerRunService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PlannerRunRepository(session)

    async def transition(
        self,
        run: PlannerRun,
        new_status: RunStatus,
        failure_code: str | None,
    ) -> PlannerRun:
        """Move ``run`` when the edge is legal. Flushes. Does not commit."""
        current = run.status
        allowed = _LEGAL.get(current, frozenset())
        if new_status not in allowed:
            raise RunTransitionError(str(current.value), new_status.value)
        run.status = new_status
        run.failure_code = failure_code
        await self.session.flush()
        return run

    async def start(
        self,
        *,
        session_id: str,
        user_id: uuid.UUID | None,
        idempotency_key: str,
        input_hash: str,
    ) -> PlannerRun:
        """Insert ``accepted``, commit, move to ``planning``, commit."""
        settings = get_settings()
        model_name = settings.LLM_MODEL
        run = await self.repo.create(
            {
                "session_id": session_id,
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "input_hash": input_hash,
                "status": RunStatus.ACCEPTED,
                "workflow_version": WORKFLOW_VERSION,
                "model_name": model_name,
                "provider": _provider_from_model(model_name),
                "fallback_reason": None,
            }
        )
        await self.session.commit()
        await self.session.refresh(run)
        await self.transition(run, RunStatus.PLANNING, None)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def _find(
        self,
        session_id: str,
        user_id: uuid.UUID | None,
        idempotency_key: str,
    ) -> PlannerRun | None:
        if user_id is not None:
            owned = await self.repo.get_by_user_key(user_id, idempotency_key)
            if owned is not None:
                return owned
            by_session = await self.repo.get_by_session_key(session_id, idempotency_key)
            if by_session is None:
                return None
            if by_session.user_id is None or by_session.user_id == user_id:
                return by_session
            return None
        return await self.repo.get_by_session_key(session_id, idempotency_key)

    async def _claim_guest(self, run: PlannerRun, user_id: uuid.UUID, key: str) -> PlannerRun:
        if run.user_id is not None:
            return run
        try:
            run.user_id = user_id
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(run)
            return run
        except IntegrityError:
            await self.session.rollback()
            winner = await self.repo.get_by_user_key(user_id, key)
            if winner is None:
                raise
            return winner

    async def resolve(
        self,
        *,
        session_id: str,
        user_id: uuid.UUID | None,
        idempotency_key: str,
        input_hash: str,
    ) -> tuple[PlannerRun, bool]:
        """Return ``(run, created)``. A losing insert re-reads the winner."""
        existing = await self._find(session_id, user_id, idempotency_key)
        if existing is not None:
            if user_id is not None and existing.user_id is None:
                existing = await self._claim_guest(existing, user_id, idempotency_key)
            return existing, False
        try:
            created = await self.start(
                session_id=session_id,
                user_id=user_id,
                idempotency_key=idempotency_key,
                input_hash=input_hash,
            )
            return created, True
        except IntegrityError:
            await self.session.rollback()
            winner = await self._find(session_id, user_id, idempotency_key)
            if winner is None:
                raise
            if user_id is not None and winner.user_id is None:
                winner = await self._claim_guest(winner, user_id, idempotency_key)
            return winner, False

    async def lock(self, run_id: uuid.UUID) -> PlannerRun | None:
        return await self.repo.lock_by_id(run_id)

    async def bind_new_trip(
        self,
        run: PlannerRun,
        trip_id: uuid.UUID,
        *,
        degraded: bool,
    ) -> None:
        """Set the terminal save status and trip id. Caller commits."""
        target = RunStatus.DEGRADED if degraded else RunStatus.COMPLETED
        await self.transition(run, target, None)
        run.trip_id = trip_id
        await self.session.flush()

    async def finish_open(
        self,
        run_id: uuid.UUID,
        status: RunStatus,
        failure_code: str | None,
    ) -> None:
        """Transition a non-terminal run and commit. No-op when already terminal."""
        run = await self.repo.get_by_id(run_id)
        if run is None or run.status in TERMINAL_RUN_STATUSES:
            return
        await self.transition(run, status, failure_code)
        await self.session.commit()

    def assert_can_access(
        self,
        run: PlannerRun,
        *,
        user_id: uuid.UUID | None,
        session_id: str | None,
    ) -> None:
        if user_id is None:
            if not session_id or session_id != run.session_id:
                raise RunForbiddenError()
            return
        if run.user_id == user_id:
            return
        if run.user_id is None and session_id and session_id == run.session_id:
            return
        raise RunForbiddenError()

    async def get_for_access(
        self,
        run_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        session_id: str | None,
    ) -> PlannerRun:
        run = await self.repo.get_by_id(run_id)
        if run is None:
            raise RunNotFoundError(str(run_id))
        self.assert_can_access(run, user_id=user_id, session_id=session_id)
        return run
