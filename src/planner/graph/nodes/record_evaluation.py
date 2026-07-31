"""Record evaluation bookend — always best-effort persist (P5.10)."""

from __future__ import annotations

from typing import Any

# Register FK targets on Base.metadata before EvaluationService writes.
import src.destinations.models  # noqa: F401
import src.trips.models  # noqa: F401

from src.core.database.session import get_session_factory
from src.core.observability.logging import get_logger
from src.evaluation.service import EvaluationService

log = get_logger()


async def record_evaluation(state: dict[str, Any]) -> dict[str, Any]:
    """Persist generation evaluation; DB failures become warnings (never raise)."""
    warnings = list(state.get("warnings") or [])
    try:
        factory = get_session_factory()
        async with factory() as session:
            service = EvaluationService(session)
            await service.record_generation(state)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — soft-fail for graph / SSE
        log.warning(
            "record_evaluation_failed",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        warnings.append("evaluation_write_failed")
        return {"warnings": warnings}
    return {}
