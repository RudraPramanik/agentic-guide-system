"""NoOpTracer path must not break generate; tracer exceptions are swallowed."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.errors import GraphRecursionError

from src.core.observability.tracing import (
    NoOpTracer,
    end_generation_trace,
    start_generation_trace,
)
from src.planner.service import PlannerService, _trace_outcome


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


@pytest.mark.asyncio
async def test_generate_calls_trace_lifecycle_on_success() -> None:
    """start → emit tool spans → end once per successful generate."""
    svc = PlannerService()
    tool_trace = [{"name": "check_readiness", "ok": True, "ms": 1}]
    fake_final = {
        "destination_id": "458854b1-4d2a-4d02-8901-e26ed59c0c8b",
        "raw_input": "1 day",
        "plan_complete": True,
        "abort_triggered": False,
        "needs_clarification": False,
        "itinerary": {"days": []},
        "tool_trace": tool_trace,
        "warnings": [],
        "errors": [],
        "token_usage": {},
    }
    start_mock = MagicMock(return_value=object())
    emit_mock = MagicMock()
    end_mock = MagicMock()

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
        patch("src.planner.service.start_generation_trace", start_mock),
        patch("src.planner.service.emit_tool_spans_from_trace", emit_mock),
        patch("src.planner.service.end_generation_trace", end_mock),
    ):
        out = await svc.generate(
            destination_id=fake_final["destination_id"],
            raw_input="1 day",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-1",
        )

    assert out["plan_complete"] is True
    start_mock.assert_called_once()
    assert start_mock.call_args.kwargs["metadata"]["destination_id"] == fake_final[
        "destination_id"
    ]
    assert start_mock.call_args.kwargs["session_id"] == "sess-1"
    emit_mock.assert_called_once_with(tool_trace)
    end_mock.assert_called_once()
    assert end_mock.call_args.kwargs["outcome"] == "success"


@pytest.mark.asyncio
async def test_generate_ends_trace_on_timeout() -> None:
    svc = PlannerService()
    start_mock = MagicMock(return_value=object())
    emit_mock = MagicMock()
    end_mock = MagicMock()

    with (
        patch(
            "src.planner.service.get_compiled_graph",
            return_value=AsyncMock(
                ainvoke=AsyncMock(side_effect=TimeoutError()),
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
            "src.planner.service.get_settings",
            return_value=MagicMock(
                PLANNER_GENERATION_TIMEOUT_SECONDS=0.01,
                PLANNER_MAX_TOOL_CALLS=10,
                PLANNER_AGENT_PHASE_STUCK_LIMIT=2,
                PLANNER_MAX_REPLAN_ATTEMPTS=2,
            ),
        ),
        patch("src.planner.service.start_generation_trace", start_mock),
        patch("src.planner.service.emit_tool_spans_from_trace", emit_mock),
        patch("src.planner.service.end_generation_trace", end_mock),
    ):
        out = await svc.generate(
            destination_id="458854b1-4d2a-4d02-8901-e26ed59c0c8b",
            raw_input="1 day",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-timeout",
        )

    assert out["abort_triggered"] is True
    assert "generation_timeout" in out["errors"]
    start_mock.assert_called_once()
    end_mock.assert_called_once()
    assert end_mock.call_args.kwargs["outcome"] == "timeout"
    emit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_generate_ends_trace_on_recursion_abort() -> None:
    svc = PlannerService()
    start_mock = MagicMock(return_value=object())
    end_mock = MagicMock()

    with (
        patch(
            "src.planner.service.get_compiled_graph",
            return_value=AsyncMock(
                ainvoke=AsyncMock(side_effect=GraphRecursionError("limit")),
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
        patch("src.planner.service.start_generation_trace", start_mock),
        patch("src.planner.service.emit_tool_spans_from_trace", MagicMock()),
        patch("src.planner.service.end_generation_trace", end_mock),
    ):
        out = await svc.generate(
            destination_id="458854b1-4d2a-4d02-8901-e26ed59c0c8b",
            raw_input="1 day",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-recur",
        )

    assert out["abort_triggered"] is True
    assert "graph_recursion_limit" in out["errors"]
    start_mock.assert_called_once()
    end_mock.assert_called_once()
    assert end_mock.call_args.kwargs["outcome"] == "recursion_abort"


def test_trace_outcome_labels() -> None:
    assert _trace_outcome({"errors": ["generation_timeout"]}) == "timeout"
    assert _trace_outcome({"errors": ["graph_recursion_limit"]}) == "recursion_abort"
    assert _trace_outcome({"needs_clarification": True, "errors": []}) == "clarification"
    assert (
        _trace_outcome(
            {"plan_complete": True, "abort_triggered": False, "errors": []}
        )
        == "success"
    )
    assert _trace_outcome({"abort_triggered": True, "errors": ["x"]}) == "error"


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


def test_end_generation_trace_updates_without_end() -> None:
    """Parent StatefulTraceClient has no end(); finalize via update only."""
    trace = MagicMock()
    trace.end = MagicMock(side_effect=AttributeError("no end"))
    with patch("src.core.observability.tracing._active_trace", trace):
        end_generation_trace(outcome="success", metadata={"destination_id": "x"})
    trace.update.assert_called_once()
    assert trace.update.call_args.kwargs["output"] == {"outcome": "success"}
    trace.end.assert_not_called()


def test_langfuse_litellm_metadata_when_active() -> None:
    trace = MagicMock()
    trace.trace_id = "abc-123"
    with (
        patch(
            "src.core.observability.tracing.is_langfuse_tracing_active",
            return_value=True,
        ),
        patch("src.core.observability.tracing._active_trace", trace),
    ):
        from src.core.observability.tracing import langfuse_litellm_metadata

        meta = langfuse_litellm_metadata(generation_name="chat_completion")
    assert meta == {
        "existing_trace_id": "abc-123",
        "generation_name": "chat_completion",
    }


def test_langfuse_litellm_metadata_none_when_inactive() -> None:
    with patch(
        "src.core.observability.tracing.is_langfuse_tracing_active",
        return_value=False,
    ):
        from src.core.observability.tracing import langfuse_litellm_metadata

        assert langfuse_litellm_metadata(generation_name="chat_completion") is None
