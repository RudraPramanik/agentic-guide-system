"""Wandr — Langfuse tracing with Null Object fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.observability.logging import get_logger

if TYPE_CHECKING:
    from langfuse import Langfuse

    from src.core.llm.client import LLMUsage

try:
    from langfuse import Langfuse as _Langfuse
except ImportError:
    _Langfuse = None  # type: ignore[misc, assignment]

log = get_logger()

_tracer: Langfuse | NoOpTracer | None = None
_tracer_error_logged: bool = False
_active_trace: Any | None = None


class NoOpTracer:
    """Null Object stand-in when Langfuse is unavailable or unconfigured."""

    def trace(self, name: str, **kwargs: Any) -> NoOpTracer:
        return self

    def span(self, name: str, **kwargs: Any) -> NoOpTracer:
        return self

    def generation(self, name: str, **kwargs: Any) -> NoOpTracer:
        return self

    def update(self, **kwargs: Any) -> NoOpTracer:
        return self

    def end(self, **kwargs: Any) -> NoOpTracer:
        return self

    def flush(self) -> None:
        return None


def _log_tracer_once(event: str, error: Exception) -> None:
    global _tracer_error_logged
    if not _tracer_error_logged:
        _tracer_error_logged = True
        log.warning(event, error=str(error))


def get_tracer() -> Langfuse | NoOpTracer:
    """Return cached Langfuse client or NoOpTracer when keys are missing."""

    global _tracer
    if _tracer is not None:
        return _tracer

    try:
        from src.config import get_settings

        settings = get_settings()
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and _Langfuse is not None:
            try:
                _tracer = _Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                )
                return _tracer
            except Exception as exc:
                log.warning("langfuse_init_failed", error=str(exc))
    except Exception as exc:
        log.warning("langfuse_init_failed", error=str(exc))

    _tracer = NoOpTracer()
    return _tracer


def flush_tracer() -> None:
    """Flush pending Langfuse events. Safe to call on shutdown."""

    try:
        get_tracer().flush()
    except Exception as exc:
        log.warning("langfuse_flush_failed", error=str(exc))


def start_generation_trace(name: str = "planner.generate", **kwargs: Any) -> Any | None:
    """Start one Langfuse trace for a planner generation. Fail-soft."""
    global _active_trace
    try:
        tracer = get_tracer()
        _active_trace = tracer.trace(name=name, **kwargs)
        return _active_trace
    except Exception as exc:
        _log_tracer_once("langfuse_trace_start_failed", exc)
        _active_trace = None
        return None


def end_generation_trace(
    *,
    outcome: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """End the active generation trace. Fail-soft."""
    global _active_trace
    trace = _active_trace
    _active_trace = None
    if trace is None:
        return
    try:
        update_kwargs: dict[str, Any] = {}
        if outcome is not None:
            update_kwargs["output"] = {"outcome": outcome}
        if metadata:
            update_kwargs["metadata"] = metadata
        if update_kwargs:
            trace.update(**update_kwargs)
        trace.end()
    except Exception as exc:
        _log_tracer_once("langfuse_trace_end_failed", exc)


def safe_generation_span(
    *,
    name: str,
    model: str,
    usage: LLMUsage,
    latency_ms: float,
    retry_count: int,
) -> None:
    """Emit a generation span under the active trace when present. Fail-soft."""
    try:
        parent = _active_trace
        tracer = get_tracer()
        kwargs: dict[str, Any] = {
            "name": name,
            "model": model,
            "metadata": {
                "latency_ms": round(latency_ms, 2),
                "retry_count": retry_count,
            },
            "usage": {
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens,
                "total": usage.total_tokens,
            },
        }
        if parent is not None and hasattr(parent, "generation"):
            gen = parent.generation(**kwargs)
        else:
            gen = tracer.generation(**kwargs)
        if hasattr(gen, "end"):
            gen.end()
    except Exception as exc:
        _log_tracer_once("langfuse_generation_span_failed", exc)


def emit_tool_spans_from_trace(tool_trace: list[dict[str, Any]] | None) -> None:
    """Post-hoc tool spans from TravelState tool_trace entries. Fail-soft."""
    if not tool_trace:
        return
    parent = _active_trace
    if parent is None:
        return
    try:
        for entry in tool_trace:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or entry.get("tool") or "tool")
            try:
                span = parent.span(
                    name=name,
                    metadata={
                        "ok": entry.get("ok"),
                        "ms": entry.get("ms"),
                        "fallback_used": entry.get("fallback_used"),
                    },
                )
                if hasattr(span, "end"):
                    span.end()
            except Exception as exc:
                _log_tracer_once("langfuse_tool_span_failed", exc)
                break
    except Exception as exc:
        _log_tracer_once("langfuse_tool_spans_failed", exc)
