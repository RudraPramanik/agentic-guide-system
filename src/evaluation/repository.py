"""Evaluation repository — persist TripEvaluation rows (P5.10)."""

from __future__ import annotations

import uuid

from src.core.database.base_repository import BaseRepository
from src.evaluation.models import TripEvaluation


class EvaluationRepository(BaseRepository[TripEvaluation, uuid.UUID]):
    """Flush-only creates for generation records."""

    async def create_generation(self, data: dict) -> TripEvaluation:
        return await self.create(data)
