"""Planner run HTTP and transition errors."""

from __future__ import annotations

from src.core.exceptions import ForbiddenError, NotFoundError, WandrError


class RunNotFoundError(NotFoundError):
    def __init__(self, run_id: str | None = None) -> None:
        details = {"run_id": run_id} if run_id else None
        super().__init__(message="Planner run not found", details=details)


class RunForbiddenError(ForbiddenError):
    def __init__(self, message: str = "Access to this run is forbidden") -> None:
        super().__init__(message=message)


class RunTransitionError(WandrError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            code="invalid_run_transition",
            message=f"Cannot move run from {current} to {target}",
            status_code=409,
            details={"from": current, "to": target},
        )
