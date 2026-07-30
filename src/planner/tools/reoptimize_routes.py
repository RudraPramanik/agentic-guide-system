"""reoptimize_routes — REPLAN; re-run route+schedule for current ranked set."""

from __future__ import annotations

from typing import Any

from src.planner.tools.build_route import run as build_route_run
from src.planner.tools.build_schedule import run as build_schedule_run
from src.planner.tools.schemas import (
    BuildRouteIn,
    BuildScheduleIn,
    ReoptimizeRoutesIn,
    ToolResult,
)


class _StateView:
    """Lightweight mutable view so nested helpers can read merged data."""

    def __init__(self, base: Any, overrides: dict) -> None:
        self._base = base
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        if self._base is None:
            raise AttributeError(name)
        if isinstance(self._base, dict):
            if name in self._base:
                return self._base[name]
            raise AttributeError(name)
        return getattr(self._base, name)


async def run(
    inp: ReoptimizeRoutesIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    route_result = await build_route_run(BuildRouteIn(), ctx, state)
    if not route_result.ok:
        return route_result
    merged = dict(route_result.data or {})
    view = _StateView(state, merged)
    sched_result = await build_schedule_run(BuildScheduleIn(), ctx, view)
    if not sched_result.ok:
        return ToolResult(
            ok=False,
            code=sched_result.code or "tool_error",
            message=sched_result.message,
            data={**merged, **(sched_result.data or {})},
            fallback_used=route_result.fallback_used,
        )
    data = {**merged, **(sched_result.data or {})}
    return ToolResult(
        ok=True,
        data=data,
        fallback_used=route_result.fallback_used or sched_result.fallback_used,
    )
