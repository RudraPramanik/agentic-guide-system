"""check_readiness — DISCOVER tool; soft-warns on low readiness."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.core.database.session import AsyncSessionLocal
from src.destinations.service import DestinationService
from src.planner.tools._helpers import as_uuid, state_get
from src.planner.tools.schemas import CheckReadinessIn, ToolResult


def _destination_id(ctx: Any, state: Any) -> Any:
    if ctx is not None and getattr(ctx, "destination_id", None) is not None:
        return getattr(ctx, "destination_id")
    return state_get(state, "destination_id")


async def run(
    inp: CheckReadinessIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    dest_id = _destination_id(ctx, state)
    if dest_id is None:
        return ToolResult(
            ok=False,
            code="precondition_failed",
            message="destination_id required",
        )

    dest_id = as_uuid(dest_id)
    own_session = False
    session = getattr(ctx, "db", None) if ctx is not None else None
    if session is None:
        session = AsyncSessionLocal()
        own_session = True

    try:
        service = DestinationService(session)
        readiness = await service.get_readiness(dest_id)
        settings = get_settings()
        warning = None
        if readiness.score < settings.PLANNER_MIN_READINESS_SCORE:
            warning = (
                f"readiness_score {readiness.score} below "
                f"PLANNER_MIN_READINESS_SCORE "
                f"{settings.PLANNER_MIN_READINESS_SCORE}"
            )
        return ToolResult(
            ok=True,
            code="low_readiness" if warning else None,
            message=warning or readiness.message,
            data={
                "readiness_score": readiness.score,
                "tier": readiness.tier,
                "place_count": readiness.place_count,
                "enriched_pct": readiness.enriched_pct,
                "indexed_pct": readiness.indexed_pct,
                "warning": warning,
            },
        )
    finally:
        if own_session:
            await session.close()
