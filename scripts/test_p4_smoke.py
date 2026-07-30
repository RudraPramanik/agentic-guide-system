"""
P4 smoke — run: python scripts/test_p4_smoke.py

Offline by default (FakeRoutingProvider). Optional live OSRM:
  OPTIONAL_LIVE_OSRM=1 python scripts/test_p4_smoke.py

Fail-fast: first failed section exits non-zero. Never ambiguous PASS.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from uuid import UUID, uuid4

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pydantic import BaseModel

from src.places.constants import PLACE_TAG_VOCAB
from src.planner.tools.registry import execute_tool
from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.place_selector import (
    PlaceCandidate,
    TripPreferences,
    select_places,
)
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.route_optimizer import optimize_route
from src.travel_engine.schedule_builder import build_day_schedule
from src.travel_engine.travel_rules import (
    BASE_SENTINEL_ID,
    CATEGORY_WEIGHTS,
    MAX_PLACES_PER_DAY,
    MORNING_ONLY_CATEGORIES,
    VISIT_DURATION_BY_CATEGORY,
    visit_duration_min,
)
from src.travel_engine.trip_validator import DayPlan, TripItinerary, validate_trip

_P2 = {"museum", "viewpoint", "monastery", "attraction", "park", "trailhead"}
_FORBIDDEN = re.compile(
    r"src\.geo|import httpx|from httpx|litellm|qdrant|sqlalchemy",
    re.IGNORECASE,
)


class _FakeRoutingProvider:
    """Deterministic offline matrix — no network."""

    def __init__(self, default_duration_min: int = 20) -> None:
        self._default_duration_min = default_duration_min
        self.call_count = 0

    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ) -> list[RouteLeg]:
        self.call_count += 1
        ids = [w[0] for w in waypoints]
        legs: list[RouteLeg] = []
        for a in ids:
            for b in ids:
                if a == b:
                    continue
                legs.append(
                    RouteLeg(
                        from_place_id=a,
                        to_place_id=b,
                        duration_min=self._default_duration_min,
                        distance_km=1.0,
                    )
                )
        return legs


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(section: str, msg: str) -> None:
    print(f"  [FAIL] {section}: {msg}")
    raise AssertionError(f"{section}: {msg}")


def section_travel_rules() -> None:
    print("\n--- 1. travel_rules constants ---")
    if not _P2 <= set(VISIT_DURATION_BY_CATEGORY):
        _fail("travel_rules", f"missing P2 categories: {_P2 - set(VISIT_DURATION_BY_CATEGORY)}")
    if visit_duration_min("unknown_future") != 30:
        _fail("travel_rules", "default duration expected 30")
    if not set(CATEGORY_WEIGHTS) <= set(PLACE_TAG_VOCAB):
        _fail("travel_rules", "CATEGORY_WEIGHTS not ⊆ PLACE_TAG_VOCAB")
    if "sunrise_point" in MORNING_ONLY_CATEGORIES:
        _fail("travel_rules", "sunrise_point must not be in MORNING_ONLY_CATEGORIES")
    _ok("duration keys, default, weights, morning-only")


def section_select() -> list:
    print("\n--- 2. select_places ---")
    prefs = TripPreferences(interests=["photography", "viewpoint", "monastery"], days=2)
    candidates = [
        PlaceCandidate(
            id=uuid4(),
            name="Tiger Hill",
            category="viewpoint",
            enriched_tags=["photography", "viewpoint"],
            lat=27.041,
            lng=88.263,
        ),
        PlaceCandidate(
            id=uuid4(),
            name="Peace Pagoda",
            category="monastery",
            enriched_tags=["monastery", "cultural"],
            lat=27.051,
            lng=88.266,
        ),
        PlaceCandidate(
            id=uuid4(),
            name="Himalayan Zoo",
            category="attraction",
            enriched_tags=["family", "nature"],
            lat=27.059,
            lng=88.255,
        ),
        PlaceCandidate(
            id=uuid4(),
            name="Batasia Loop",
            category="viewpoint",
            enriched_tags=["photography"],
            lat=27.033,
            lng=88.246,
        ),
        PlaceCandidate(
            id=uuid4(),
            name="Padmaja Park",
            category="park",
            enriched_tags=[],
            lat=27.048,
            lng=88.260,
        ),
        PlaceCandidate(
            id=uuid4(),
            name="Tea Museum",
            category="museum",
            enriched_tags=["cultural"],
            lat=27.045,
            lng=88.268,
        ),
    ]
    scored = select_places(candidates, prefs)
    if not scored:
        _fail("select_places", "empty result")
    if scored[0].place.name != "Tiger Hill":
        _fail("select_places", f"expected Tiger Hill first, got {scored[0].place.name}")
    zero = next((s for s in scored if s.place.name == "Padmaja Park"), None)
    if zero is None or zero.score != 0:
        _fail("select_places", "empty-tags place should score 0 and remain")
    _ok(f"{len(scored)} scored; top={scored[0].place.name} score={scored[0].score}")
    return scored


def section_allocate(scored: list) -> list:
    print("\n--- 3. allocate_days ---")
    days = allocate_days(scored, 2)
    if len(days) != 2:
        _fail("allocate_days", f"expected 2 day lists, got {len(days)}")
    if any(len(d) > MAX_PLACES_PER_DAY for d in days):
        _fail("allocate_days", "day exceeded MAX_PLACES_PER_DAY")
    _ok(f"day sizes {[len(d) for d in days]}")
    return days


async def section_optimize(day_places: list):
    print("\n--- 4. optimize_route (Fake) ---")
    fake = _FakeRoutingProvider(default_duration_min=20)
    base_lat, base_lng = 27.041, 88.263
    result = await optimize_route(day_places, base_lat, base_lng, fake)
    if len(result.ordered) != len(day_places):
        _fail(
            "optimize_route",
            f"ordered={len(result.ordered)} vs input={len(day_places)}",
        )
    if fake.call_count < 1:
        _fail("optimize_route", "Fake travel_matrix never called")
    _ok(
        f"ordered={[s.place.name for s in result.ordered]} "
        f"travel={result.total_travel_min}m drops={len(result.dropped_stops)}"
    )
    return result, fake, base_lat, base_lng


async def section_schedule(opt, fake, base_lat: float, base_lng: float) -> list:
    print("\n--- 5. build_day_schedule ---")
    # Morning-only extract may reorder stops — pass full pairwise matrix
    # (lookup-complete), not only consecutive OptimizeResult.legs.
    waypoints = [
        (BASE_SENTINEL_ID, base_lat, base_lng),
        *[(s.place.id, s.place.lat, s.place.lng) for s in opt.ordered],
    ]
    full_legs = await fake.travel_matrix(waypoints)
    schedule = build_day_schedule(opt.ordered, full_legs)
    if len(schedule) != len(opt.ordered):
        _fail("build_day_schedule", "schedule length mismatch")
    if schedule[0].suggested_start_time < "08:00":
        _fail("build_day_schedule", f"first start {schedule[0].suggested_start_time}")
    _ok(
        f"{len(schedule)} stops; first={schedule[0].place.name} "
        f"@{schedule[0].suggested_start_time}"
    )
    return schedule


def section_validate(schedule: list, opt) -> None:
    print("\n--- 6. validate_trip ---")
    itinerary = TripItinerary(
        days=[
            DayPlan(
                stops=schedule,
                total_travel_min=opt.total_travel_min,
                dropped_stops=opt.dropped_stops,
            )
        ]
    )
    result = validate_trip(itinerary)
    if not result.passed:
        _fail("validate_trip", f"errors={result.errors}")
    _ok(f"passed=True warnings={result.warnings}")


async def section_execute_tool() -> None:
    print("\n--- 7. execute_tool unknown ---")

    class Empty(BaseModel):
        pass

    r = await execute_tool("no_such_tool", Empty())
    if r.ok is not False:
        _fail("execute_tool", f"expected ok=False, got {r}")
    if r.code != "unknown_tool":
        _fail("execute_tool", f"expected code=unknown_tool, got {r.code}")
    _ok(f"ok=False code={r.code}")


def section_purity() -> None:
    print("\n--- 8. travel_engine import guard ---")
    engine = _ROOT / "src" / "travel_engine"
    hits: list[str] = []
    for path in sorted(engine.rglob("*.py")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _FORBIDDEN.search(line):
                hits.append(f"{path.relative_to(_ROOT)}:{i}: {line.strip()}")
    if hits:
        _fail("purity", "\n".join(hits))
    _ok("no geo/httpx/litellm/qdrant/sqlalchemy imports")


async def section_live_osrm() -> None:
    print("\n--- 9. OPTIONAL_LIVE_OSRM ---")
    if os.environ.get("OPTIONAL_LIVE_OSRM") != "1":
        print("  [SKIP] set OPTIONAL_LIVE_OSRM=1 to exercise OsrmRoutingProvider")
        return
    from src.planner.routing_provider import OsrmRoutingProvider

    a, b, c = uuid4(), uuid4(), uuid4()
    waypoints = [
        (a, 27.041, 88.263),
        (b, 27.051, 88.266),
        (c, 27.059, 88.255),
    ]
    provider = OsrmRoutingProvider()
    legs = await provider.travel_matrix(waypoints)
    expected = 3 * 2  # directed pairwise
    if len(legs) != expected:
        _fail("live_osrm", f"expected {expected} legs, got {len(legs)}")
    _ok(f"{len(legs)} pairwise legs (fallback allowed)")


async def main() -> int:
    print("P4 smoke — offline Fake pipeline")
    try:
        section_travel_rules()
        scored = section_select()
        days = section_allocate(scored)
        day0 = days[0] if days[0] else scored[:3]
        opt, fake, base_lat, base_lng = await section_optimize(day0)
        schedule = await section_schedule(opt, fake, base_lat, base_lng)
        section_validate(schedule, opt)
        await section_execute_tool()
        section_purity()
        await section_live_osrm()
    except AssertionError as exc:
        print(f"\nP4 SMOKE FAILED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors loudly
        print(f"\nP4 SMOKE FAILED (unexpected): {type(exc).__name__}: {exc}")
        return 1

    print("\nALL P4 SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
