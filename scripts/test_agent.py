"""
P5 smoke — run: python scripts/test_agent.py

Requires: LLM keys in .env, seeded+enriched+indexed Darjeeling in DB,
Postgres :5433, Qdrant :6335.

Prefer: PlannerService.generate(...) (no HTTP router).
Fail-fast: first failed section exits non-zero. Never ambiguous PASS.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select

from src.config import get_settings
from src.core.database.session import get_session_factory
from src.destinations.models import Destination
from src.evaluation.models import TripEvaluation
from src.planner.graph.builder import build_planner_graph, get_compiled_graph
from src.planner.service import PlannerService

_RAW = "3 days offbeat photography budget"
_DEST_NAME = "Darjeeling"


def _fail(section: str, msg: str) -> None:
    print(f"FAIL — {section}: {msg}")
    sys.exit(1)


def _ok(section: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"PASS — {section}{suffix}")


def section_1_settings() -> None:
    print("\n=== 1) settings planner bounds ===")
    s = get_settings()
    for name in (
        "PLANNER_MAX_TOOL_CALLS",
        "PLANNER_MAX_REPLAN_ATTEMPTS",
        "PLANNER_GENERATION_TIMEOUT_SECONDS",
        "PLANNER_MIN_READINESS_SCORE",
        "PLANNER_AGENT_PHASE_STUCK_LIMIT",
        "LLM_API_KEY",
    ):
        if not hasattr(s, name) or getattr(s, name) in (None, ""):
            _fail("1 settings", f"missing {name}")
    _ok("1 settings", "planner bounds + LLM key present")


def section_2_graph_compiles() -> None:
    print("\n=== 2) graph compiles ===")
    g = build_planner_graph()
    assert g is not None
    cached = get_compiled_graph()
    assert cached is not None
    _ok("2 graph", type(g).__name__)


async def _resolve_darjeeling() -> tuple[str, float, float]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Destination).where(Destination.name.ilike(_DEST_NAME)).limit(1)
        )
        dest = result.scalar_one_or_none()
        if dest is None:
            _fail(
                "3 generate",
                f"destination '{_DEST_NAME}' not found — seed/enrich/index first",
            )
        return str(dest.id), float(dest.lat), float(dest.lng)


async def section_3_to_7() -> dict:
    print("\n=== 3) generate() completes ===")
    dest_id, lat, lng = await _resolve_darjeeling()

    # Same infra as FastAPI lifespan — without this, is_qdrant_available() stays
    # False and search_places always geo-falls back (weak smoke itineraries).
    from src.search.client import ensure_places_collection, is_qdrant_available
    from src.search.embeddings import ensure_embedding_model_loaded

    await ensure_places_collection()
    await ensure_embedding_model_loaded()
    if not is_qdrant_available():
        _fail(
            "3 generate",
            "Qdrant not available after ensure_places_collection — "
            "start docker compose (Qdrant :6335) and re-index if needed",
        )

    events: list[str] = []

    def on_event(event: str, data: dict) -> None:
        events.append(event)

    svc = PlannerService()
    try:
        final = await svc.generate(
            destination_id=dest_id,
            raw_input=_RAW,
            base_lat=lat,
            base_lng=lng,
            session_id="p5-smoke-session",
            on_event=on_event,
        )
    except Exception as exc:  # noqa: BLE001
        _fail("3 generate", f"{type(exc).__name__}: {exc}")

    _ok("3 generate", f"events={len(events)} phase={final.get('agent_phase')}")

    print("\n=== 4) errors / abort ===")
    errors = list(final.get("errors") or [])
    hard = [e for e in errors if e not in ("evaluation_write_failed",)]
    if hard:
        _fail("4 errors", str(hard))
    if final.get("abort_triggered"):
        _fail("4 abort", "abort_triggered=True")
    _ok("4 errors", "clean")

    print("\n=== 5) days + stop fields ===")
    days = int(final.get("days") or 0)
    if days != 3:
        _fail("5 days", f"expected days==3 got {days}")
    schedule = final.get("schedule") or []
    itinerary = final.get("itinerary") or {}
    day_list = itinerary.get("days") if isinstance(itinerary, dict) else None

    def _day_stops(day: object) -> list:
        # build_schedule stores list[list[stop_dict]]; narrative days use dicts.
        if isinstance(day, list):
            return day
        if isinstance(day, dict):
            return day.get("stops") or day.get("places") or []
        return []

    def _stop_lat_lng(stop: dict) -> tuple[object, object]:
        if stop.get("lat") is not None and stop.get("lng") is not None:
            return stop.get("lat"), stop.get("lng")
        place = stop.get("place") or {}
        if isinstance(place, dict):
            return place.get("lat"), place.get("lng")
        return None, None

    stops_source = schedule if schedule else day_list
    if not stops_source:
        _fail("5 stops", "empty schedule/itinerary days")
    for day in stops_source:
        stops = _day_stops(day)
        if isinstance(day, dict) and not stops and "stops" not in day:
            # narrative-only day entry — check schedule instead
            continue
        for stop in stops:
            if not isinstance(stop, dict):
                _fail("5 stops", f"non-dict stop: {stop}")
            lat, lng = _stop_lat_lng(stop)
            if lat is None or lng is None:
                _fail("5 stops", f"missing lat/lng: {stop}")
            if not stop.get("suggested_start_time"):
                _fail("5 stops", f"missing suggested_start_time: {stop}")
    _ok("5 days", f"days={days} schedule_days={len(schedule)}")

    print("\n=== 6) tool_trace ===")
    trace = final.get("tool_trace") or []
    if not trace:
        _fail("6 tool_trace", "empty")
    print(f"{'name':<22} {'ok':<6} {'ms':>8} {'phase':<12} code")
    for t in trace:
        if not isinstance(t, dict):
            continue
        print(
            f"{str(t.get('name')):<22} {str(t.get('ok')):<6} "
            f"{float(t.get('ms') or 0):8.1f} {str(t.get('phase')):<12} {t.get('code')}"
        )
    _ok("6 tool_trace", f"len={len(trace)}")

    print("\n=== 7) evaluation row ===")
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(TripEvaluation)
            .where(TripEvaluation.destination_id == dest_id)
            .order_by(TripEvaluation.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            # destination_id may be UUID type
            from uuid import UUID

            result = await session.execute(
                select(TripEvaluation)
                .where(TripEvaluation.destination_id == UUID(dest_id))
                .order_by(TripEvaluation.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
        if row is None:
            _fail("7 evaluation", "no TripEvaluation row for destination")
        if not (row.tool_trace or []):
            _fail("7 evaluation", "tool_trace empty on evaluation row")
    _ok("7 evaluation", f"id={row.id}")
    return final


def section_8_import_guards() -> None:
    print("\n=== 8) import guards ===")
    src = _ROOT / "src"
    litellm_re = re.compile(r"import litellm|from litellm")
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if litellm_re.search(text):
            if path.name == "client.py" and "llm" in path.parts:
                continue
            _fail("8 litellm", str(path))

    tool_impl = re.compile(
        r"from src\.planner\.tools\.(check_readiness|search_places|rank_places|"
        r"build_route|build_schedule)"
    )
    for path in (src / "planner" / "graph" / "nodes").rglob("*.py"):
        if tool_impl.search(path.read_text(encoding="utf-8")):
            _fail("8 tool-impl", str(path))

    purity = re.compile(r"src\.geo|import httpx|from httpx|litellm|qdrant", re.I)
    for path in (src / "travel_engine").rglob("*.py"):
        if purity.search(path.read_text(encoding="utf-8")):
            _fail("8 travel_engine", str(path))

    from src.main import create_app

    app = create_app()
    paths = [getattr(r, "path", None) for r in app.routes]
    if any(p and "planner/generate" in p for p in paths):
        _fail("8 router", "planner/generate registered — P6 only")
    _ok("8 import guards", "litellm / tool-impl / purity / no HTTP generate")


def section_9_langfuse_optional() -> None:
    print("\n=== 9) Langfuse (optional) ===")
    s = get_settings()
    if s.LANGFUSE_PUBLIC_KEY and s.LANGFUSE_SECRET_KEY:
        print("Langfuse keys configured — check dashboard for recent traces")
    else:
        print("SKIP — Langfuse keys not configured")


async def _async_main() -> None:
    section_1_settings()
    section_2_graph_compiles()
    await section_3_to_7()
    section_8_import_guards()
    section_9_langfuse_optional()
    print("\nALL PASSED — P5 smoke")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
