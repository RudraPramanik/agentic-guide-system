"""Wandr — Langfuse tracing with Null Object fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.observability.logging import get_logger

if TYPE_CHECKING:
    from langfuse import Langfuse

try:
    from langfuse import Langfuse as _Langfuse
except ImportError:
    _Langfuse = None  # type: ignore[misc, assignment]

log = get_logger()

_tracer: Langfuse | NoOpTracer | None = None


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
