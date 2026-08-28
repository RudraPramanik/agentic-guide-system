"""Send one Langfuse connectivity test trace when keys are configured."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import get_settings
from src.core.observability.tracing import (
    end_generation_trace,
    flush_tracer,
    get_tracer,
    is_langfuse_tracing_active,
    start_generation_trace,
)


def main() -> int:
    settings = get_settings()
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        print("skip: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY empty (NoOp path)")
        return 0

    tracer = get_tracer()
    if not is_langfuse_tracing_active():
        print("fail: keys set but tracer is NoOp — check langfuse package and host")
        return 1

    trace = start_generation_trace(
        name="prove_langfuse.connectivity",
        session_id="prove-langfuse-script",
        metadata={"source": "scripts/prove_langfuse.py"},
    )
    if trace is None:
        print("fail: could not start test trace")
        return 1

    end_generation_trace(outcome="ok", metadata={"host": settings.LANGFUSE_HOST})
    flush_tracer()
    trace_id = getattr(trace, "trace_id", None) or getattr(trace, "id", "unknown")
    print(f"ok: test trace sent (trace_id={trace_id}, host={settings.LANGFUSE_HOST})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
