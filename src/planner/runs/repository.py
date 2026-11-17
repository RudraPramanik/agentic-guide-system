"""Planner run repository. Flush-only writes; no status transitions."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.core.database.base_repository import BaseRepository
from src.planner.runs.models import PlannerRun


class PlannerRunRepository(BaseRepository[PlannerRun, uuid.UUID]):
    async def get_by_session_key(
        self,
        session_id: str,
        idempotency_key: str,
    ) -> PlannerRun | None:
        stmt = select(PlannerRun).where(
            PlannerRun.session_id == session_id,
            PlannerRun.idempotency_key == idempotency_key,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_user_key(
        self,
        user_id: uuid.UUID,
        idempotency_key: str,
    ) -> PlannerRun | None:
        stmt = select(PlannerRun).where(
            PlannerRun.user_id == user_id,
            PlannerRun.idempotency_key == idempotency_key,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def lock_by_id(self, run_id: uuid.UUID) -> PlannerRun | None:
        stmt = select(PlannerRun).where(PlannerRun.id == run_id).with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()
