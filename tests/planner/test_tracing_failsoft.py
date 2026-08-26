"""NoOpTracer path must not break generate; tracer exceptions are swallowed."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.observability.tracing import (
    NoOpTracer,
    end_generation_trace,
    start_generation_trace,
)
from src.planner.service import PlannerService


@pytest.mark.asyncio
async def test_generate_with_noop_tracer_completes() -> None:
    """Empty Langfuse keys → NoOpTracer; generate still returns a state dict."""
    svc = PlannerService()
    fake_final = {
        "destination_id": "458854b1-4d2a-4d02-8901-e26ed59c0c8b",
        "raw_input": "1 day",
        "plan_complete": True,
        "itinerary": {"days": []},
        "tool_trace": [{"name": "check_readiness", "ok": True, "ms": 1}],
        "warnings": [],
        "errors": [],
        "token_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "llm_retry_count": 0,
    }

    with (
        patch(
            "src.planner.service.get_compiled_graph",
            return_value=AsyncMock(
                ainvoke=AsyncMock(return_value=fake_final),
            ),
        ),
        patch(
            "src.planner.service.record_evaluation",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "src.planner.service.get_routing_provider",
            return_value=object(),
        ),
        patch(
            "src.core.observability.tracing.get_tracer",
            return_value=NoOpTracer(),
        ),
    ):
        out = await svc.generate(
            destination_id=fake_final["destination_id"],
            raw_input="1 day",
            base_lat=27.0,
            base_lng=88.0,
            session_id="test-session",
        )
    assert out["plan_complete"] is True
    assert out["token_usage"]["total_tokens"] == 2


def test_tracer_exception_does_not_raise() -> None:
    class Boom:
        def trace(self, *a, **k):
            raise RuntimeError("boom")

        def flush(self):
            raise RuntimeError("boom")

    with patch(
        "src.core.observability.tracing.get_tracer",
        return_value=Boom(),
    ):
        assert start_generation_trace() is None
        end_generation_trace(outcome="aborted")  # must not raise
