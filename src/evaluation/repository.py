"""Evaluation repository — persist TripEvaluation rows (P5.10 / P7.5)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from src.core.database.base_repository import BaseRepository
from src.evaluation.models import TripEvaluation


class EvaluationRepository(BaseRepository[TripEvaluation, uuid.UUID]):
    """Flush-only creates for generation records; flag helpers for edits."""

    async def create_generation(self, data: dict) -> TripEvaluation:
        return await self.create(data)

    async def get_latest_for_trip(self, trip_id: uuid.UUID) -> TripEvaluation | None:
        """Return newest TripEvaluation for trip_id, or None."""
        stmt = (
            select(TripEvaluation)
            .where(TripEvaluation.trip_id == trip_id)
            .order_by(TripEvaluation.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def mark_user_edited(self, evaluation: TripEvaluation) -> TripEvaluation:
        """Set user_edited=True on the given row. Flush-only."""
        evaluation.user_edited = True
        await self.session.flush()
        return evaluation
