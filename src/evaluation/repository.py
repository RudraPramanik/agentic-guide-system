"""Evaluation repository — persist TripEvaluation rows (P5.10)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.core.database.base_repository import BaseRepository
from src.evaluation.models import TripEvaluation


class EvaluationRepository(BaseRepository[TripEvaluation, uuid.UUID]):
    """Flush-only creates for generation records."""

    async def create_generation(self, data: dict) -> TripEvaluation:
        return await self.create(data)

    async def mark_user_edited(self, trip_id: uuid.UUID) -> None:
        """Set user_edited=True on latest evaluation for trip, if any. Flush-only."""
        stmt = (
            select(TripEvaluation)
            .where(TripEvaluation.trip_id == trip_id)
            .order_by(TripEvaluation.created_at.desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.user_edited = True
        await self.session.flush()
