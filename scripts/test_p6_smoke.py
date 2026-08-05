"""
P6 smoke - run: python scripts/test_p6_smoke.py

Requires: Postgres :5433 (docker compose), seeded destination with
place_count >= PLANNER_ABSOLUTE_MIN_PLACES, LLM keys for generate sections.

Fail-fast: first failed section exits non-zero. Never ambiguous PASS.
Empty REDIS_URL is fine (in-memory cache/rate-limit).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Live agent loops often exceed the 45s default under public OSRM + LLM latency.
os.environ.setdefault("PLANNER_GENERATION_TIMEOUT_SECONDS", "180")

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from httpx import ASGITransport, AsyncClient

from src.auth.models import User
from src.auth.router import COOKIE_SESSION
from src.config import get_settings
from src.core.database.session import dispose_engine, get_session_factory
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.main import create_app

get_settings.cache_clear()

_DEST_QUERY = "Darjeeling"
_RAW = "2 day photography budget mid"


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(section: str, msg: str) -> None:
    print(f"  [FAIL] {section}: {msg}")
    raise AssertionError(f"{section}: {msg}")


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    blocks = re.split(r"\n\n+", text.strip())
    for block in blocks:
        if not block.strip():
            continue
        event_name = None
        data_line = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_line = line[len("data:") :].strip()
        if event_name and data_line is not None:
            try:
                payload = json.loads(data_line)
            except json.JSONDecodeError:
                payload = {"raw": data_line}
            events.append((event_name, payload))
    return events


def section_import_guards() -> None:
    print("\n--- 6. Import guards ---")
    forbidden_redis = re.compile(r"(^|\n)\s*(import redis|from redis)")
    for rel in ("src/planner", "src/trips"):
        root = _ROOT / rel
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if forbidden_redis.search(text):
                _fail("import guards", f"redis import in {path}")

    service = (_ROOT / "src/planner/service.py").read_text(encoding="utf-8")
    if "StreamingResponse" in service or "is_disconnected" in service:
        _fail("import guards", "StreamingResponse/is_disconnected in planner/service.py")

    litellm_hits = []
    for path in (_ROOT / "src").rglob("*.py"):
        if path.as_posix().endswith("core/llm/client.py"):
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(^|\n)\s*(import litellm|from litellm)", text):
            litellm_hits.append(str(path))
    if litellm_hits:
        _fail("import guards", f"litellm outside client.py: {litellm_hits}")

    te_hits = []
    te_pat = re.compile(r"src\.geo|import httpx|from httpx|litellm|qdrant", re.I)
    for path in (_ROOT / "src/travel_engine").rglob("*.py"):
        if te_pat.search(path.read_text(encoding="utf-8")):
            te_hits.append(str(path))
    if te_hits:
        _fail("import guards", f"travel_engine impurity: {te_hits}")

    _ok("redis/litellm/travel_engine/service purity clean")


async def section_catalog(client: AsyncClient) -> str:
    print("\n--- 1. Destinations search + readiness + places ---")
    r = await client.get("/api/v1/destinations/search", params={"q": _DEST_QUERY})
    if r.status_code != 200:
        _fail("search", f"status={r.status_code} body={r.text[:200]}")
    data = r.json()
    items = data.get("data") or []
    if not isinstance(items, list) or not items:
        _fail("search", f"no destinations for q={_DEST_QUERY}; body={data}")

    dest_id = str(items[0].get("id") or items[0].get("destination_id"))
    _ok(f"search -> dest_id={dest_id}")

    ready = await client.get(f"/api/v1/destinations/{dest_id}/readiness")
    if ready.status_code != 200:
        _fail("readiness", f"status={ready.status_code}")
    _ok("readiness 200")

    places = await client.get(
        "/api/v1/places",
        params={"destination_id": dest_id, "page": 1, "page_size": 5},
    )
    if places.status_code != 200:
        _fail("places", f"status={places.status_code}")
    _ok("places page 200")
    return dest_id


async def section_generate(
    client: AsyncClient, dest_id: str
) -> tuple[str, str, list[tuple[str, dict]]]:
    """
    Prove SSE + save + trip_id through the real router.

    Default: deterministic PlannerService.generate mock (reliable CI/ship gate).
    Set WANDR_P6_LIVE_LLM=1 to exercise the live agent (needs LLM + can take minutes).
    Live agent loop remains covered by scripts/test_agent.py (P5.14).
    """
    print("\n--- 2. POST /planner/generate SSE ---")
    from unittest.mock import AsyncMock, patch
    from uuid import UUID

    from sqlalchemy import select

    from src.places.models import Place

    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        dest = await session.get(Destination, UUID(str(dest_id)))
        if dest is None:
            _fail("generate", f"destination {dest_id} missing in DB")
        if dest.place_count < settings.PLANNER_ABSOLUTE_MIN_PLACES:
            _fail(
                "generate",
                f"place_count={dest.place_count} < {settings.PLANNER_ABSOLUTE_MIN_PLACES}",
            )
        result = await session.execute(
            select(Place)
            .where(Place.destination_id == dest.id, Place.deleted_at.is_(None))
            .limit(2)
        )
        places = list(result.scalars().all())
        if len(places) < 1:
            _fail("generate", "need at least 1 place for saveable schedule")
        place_rows = [
            {
                "id": str(p.id),
                "name": p.name,
                "lat": float(dest.lat),
                "lng": float(dest.lng) + i * 0.01,
            }
            for i, p in enumerate(places)
        ]

    live = os.environ.get("WANDR_P6_LIVE_LLM", "").strip() in ("1", "true", "True")

    async def _fake_generate(**kwargs):
        on_event = kwargs["on_event"]
        on_event("preferences_done", {"days": 1, "interests": ["photography"]})
        on_event("phase_changed", {"phase": "DISCOVER"})
        on_event("tool_started", {"tool": "search_places"})
        on_event("tool_done", {"tool": "search_places", "ok": True})
        on_event("phase_changed", {"phase": "WRAP_UP"})
        on_event("itinerary_done", {"title": "P6 smoke itinerary"})
        stops = []
        for i, pr in enumerate(place_rows):
            stops.append(
                {
                    "place_id": pr["id"],
                    "name": pr["name"],
                    "lat": pr["lat"],
                    "lng": pr["lng"],
                    "category": "attraction",
                    "order": i,
                    "travel_time_min": 10 * i,
                    "visit_duration_min": 60,
                    "suggested_start_time": f"{9 + i:02d}:00",
                    "arrival_note": None,
                    "leg_polyline": None,
                }
            )
        return {
            "destination_id": str(dest_id),
            "schedule": [
                {
                    "day": 1,
                    "stops": stops,
                    "total_distance_km": 1.0,
                    "total_travel_min": 10,
                    "day_polyline": None,
                }
            ],
            "itinerary": {"title": "P6 smoke itinerary"},
            "interests": ["photography"],
            "budget": "mid",
            "include_offbeat": False,
            "include_trekking": False,
            "days": 1,
            "plan_complete": True,
            "abort_triggered": False,
        }

    from contextlib import nullcontext

    patch_ctx = (
        patch(
            "src.planner.router.PlannerService.generate",
            new=AsyncMock(side_effect=_fake_generate),
        )
        if not live
        else nullcontext()
    )

    with patch_ctx:
        response = await client.post(
            "/api/v1/planner/generate",
            json={"destination_id": dest_id, "raw_input": _RAW},
            timeout=240.0 if live else 30.0,
        )
    if response.status_code != 200:
        _fail("generate", f"status={response.status_code} body={response.text[:300]}")
    if response.headers.get("cache-control") != "no-cache":
        _fail("generate", "missing Cache-Control: no-cache")
    if response.headers.get("x-accel-buffering") != "no":
        _fail("generate", "missing X-Accel-Buffering: no")

    events = _parse_sse(response.text)
    names = [e for e, _ in events]
    if not live:
        if "tool_started" not in names or "tool_done" not in names:
            _fail("generate", f"expected tool events; got {names}")
    terminals = [e for e in names if e in ("itinerary_done", "error", "clarification_needed")]
    if len(terminals) != 1:
        _fail("generate", f"expected exactly one terminal, got {terminals}")
    if terminals[0] != "itinerary_done":
        _fail("generate", f"expected itinerary_done, got {terminals[0]} payload={events[-1]}")
    terminal_payload = next(p for e, p in events if e == "itinerary_done")
    trip_id = terminal_payload.get("trip_id")
    if not trip_id:
        _fail("generate", f"itinerary_done missing trip_id: {terminal_payload}")
    session_cookie = response.cookies.get(COOKIE_SESSION) or ""
    mode = "live LLM" if live else "deterministic mock"
    _ok(f"SSE tools streamed ({mode}); itinerary_done trip_id={trip_id}")
    return trip_id, session_cookie, events


async def section_geojson(client: AsyncClient, trip_id: str) -> None:
    print("\n--- 3. GET trip geojson ---")
    r = await client.get(f"/api/v1/trips/{trip_id}/geojson")
    if r.status_code != 200:
        _fail("geojson", f"status={r.status_code}")
    body = r.json()
    if body.get("type") != "FeatureCollection":
        _fail("geojson", f"not FeatureCollection: {body.get('type')}")
    features = body.get("features") or []
    lines = [f for f in features if f.get("geometry", {}).get("type") == "LineString"]
    points = [f for f in features if f.get("geometry", {}).get("type") == "Point"]
    if not points:
        _fail("geojson", "expected Point features")
    # LineString preferred when OSRM geometry existed; Points-only is acceptable degrade
    if lines:
        _ok(f"FeatureCollection with {len(lines)} LineString(s) + {len(points)} Point(s)")
    else:
        _ok(f"FeatureCollection Points-only ({len(points)}) - OSRM polyline degrade OK")


async def section_cache_hit(client: AsyncClient, dest_id: str, first_trip_id: str) -> None:
    print("\n--- 4. Second identical generate (cache path) ---")
    response = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": dest_id, "raw_input": _RAW},
        timeout=120.0,
    )
    if response.status_code != 200:
        _fail("cache", f"status={response.status_code}")
    events = _parse_sse(response.text)
    names = [e for e, _ in events]
    if "tool_started" in names or "tool_done" in names:
        _fail("cache", f"cache hit should skip tool events; got {names}")
    if names.count("itinerary_done") != 1:
        _fail("cache", f"expected one itinerary_done; events={names}")
    payload = next(p for e, p in events if e == "itinerary_done")
    trip_id = payload.get("trip_id")
    if not trip_id:
        _fail("cache", "missing trip_id on cache hit")
    if trip_id == first_trip_id:
        _fail("cache", "cache hit reused trip_id - must persist a NEW trip")
    _ok(f"cache hit -> new trip_id={trip_id} (no tool_*)")


async def section_claim(client: AsyncClient, trip_id: str, session_id: str) -> None:
    print("\n--- 5. Claim flow ---")
    if not session_id:
        _fail("claim", "missing wandr_session from generate")

    factory = get_session_factory()
    async with factory() as session:
        user = User(
            email=f"p6-smoke-{trip_id[:8]}@wandr.dev",
            name="P6 Smoke",
            google_id=f"smoke-{trip_id}",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(user.id, user.email)
        user_id = user.id

    client.cookies.set(COOKIE_SESSION, session_id)
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post(f"/api/v1/trips/{trip_id}/claim", headers=headers)
    if first.status_code != 200:
        _fail("claim", f"expected 200, got {first.status_code} {first.text[:200]}")
    body = first.json()
    claimed_uid = (body.get("data") or {}).get("user_id")
    if str(claimed_uid) != str(user_id):
        _fail("claim", f"user_id not set on trip: {claimed_uid}")
    _ok("claim 200")

    again = await client.post(f"/api/v1/trips/{trip_id}/claim", headers=headers)
    if again.status_code != 409:
        _fail("claim", f"re-claim expected 409, got {again.status_code}")
    _ok("re-claim 409")


async def async_main() -> None:
    print("P6 smoke starting...")
    section_import_guards()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        dest_id = await section_catalog(client)
        trip_id, session_id, _events = await section_generate(client, dest_id)
        await section_geojson(client, trip_id)
        await section_cache_hit(client, dest_id, trip_id)
        await section_claim(client, trip_id, session_id)

    await dispose_engine()
    print("\nP6 SMOKE PASS")


def main() -> None:
    try:
        asyncio.run(async_main())
    except AssertionError as exc:
        print(f"\nP6 SMOKE FAIL: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nP6 SMOKE FAIL (unexpected): {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
