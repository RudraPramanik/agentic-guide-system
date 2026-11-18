"""Shared invocation budget and per-call deadline for Slice 7 roles."""

from __future__ import annotations

from src.config import get_settings


def role_deadline_seconds() -> float:
    settings = get_settings()
    return float(
        min(
            settings.LLM_TIMEOUT_SECONDS,
            settings.PLANNER_GENERATION_TIMEOUT_SECONDS // 5,
        )
    )


class InvocationBudget:
    """Counts reasoner + critic calls only (not the agent tool loop)."""

    def __init__(self, max_invocations: int | None = None) -> None:
        settings = get_settings()
        self.max_invocations = (
            int(settings.ORCHESTRATION_MAX_AGENT_INVOCATIONS)
            if max_invocations is None
            else int(max_invocations)
        )
        self.used = 0

    def remaining(self) -> int:
        return max(0, self.max_invocations - self.used)

    def try_consume(self) -> bool:
        if self.used >= self.max_invocations:
            return False
        self.used += 1
        return True
