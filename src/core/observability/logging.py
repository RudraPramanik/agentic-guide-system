"""Wandr — structured logging configuration."""

import structlog

_configured = False


def _get_renderer() -> structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer:
    try:
        from src.config import get_settings

        if get_settings().ENVIRONMENT == "production":
            return structlog.processors.JSONRenderer()
    except Exception:
        pass
    return structlog.dev.ConsoleRenderer(colors=True)


def configure_logging() -> None:
    """Configure structlog once per process. Safe to call multiple times."""

    global _configured
    if _configured:
        return

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _get_renderer(),
        ],
        wrapper_class=structlog.BoundLogger,
    )
    _configured = True


get_logger = structlog.get_logger
