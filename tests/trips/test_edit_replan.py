"""P7.4 full edit/replan pytest — FakeRoutingProvider, no live OSRM/LLM."""

from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.auth.models import User
from src.core.middleware.rate_limit import _reset_rate_limiter_for_tests
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.places.models import Place
from src.travel_engine.travel_rules import BASE_SENTINEL_ID, MAX_DAILY_TRAVEL_MIN
from src.trips.exceptions import (
    TripEditValidationError,
    TripForbiddenError,
    TripStopConflictError,
    TripStopNotFoundError,
)
from src.trips.models import EditType, Trip, TripEditEvent, TripPlace, TripStatus
from src.trips.service import TripService
from tests.travel_engine.fake_routing import FakeRoutingProvider

# ---------------------------------------------------------------------------
# Helpers — Fake only; never OsrmRoutingProvider / LLM
# ---------------------------------------------------------------------------


class _SpyFake(FakeRoutingProvider):
    """Records place IDs seen in travel_matrix (excluding base sentinel)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.matrix_place_ids: list[set[UUID]] = []

    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ):
        ids = {w[0] for w in waypoints if w[0] != BASE_SENTINEL_ID}
        self.matrix_place_ids.append(ids)
        return await super().travel_matrix(waypoints)


class _TripEditKeyedLimiter:
    """Deny after ``allow_count`` checks on ``*:trip_edit`` keys only."""

    def __init__(self, allow_count: int) -> None:
        self.allow_count = allow_count
        self.edit_calls = 0

    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        if not key.endswith(":trip_edit"):
            return True, limit
        self.edit_calls += 1
        if self.edit_calls <= self.allow_count:
            return True, max(0, self.allow_count - self.edit_calls)
        return False, 0


def _late_morning_duration(a: UUID, b: UUID) -> tuple[int, float]:
    """Base→stop long enough that a morning-only stop starts after 10:30."""
    if a == BASE_SENTINEL_ID:
        return 160, 1.0
    return 10, 1.0


async def _count_edit_events(db_session, trip_id: UUID) -> int:
    return (
        await db_session.execute(
            select(func.count())
            .select_from(TripEditEvent)
            .where(TripEditEvent.trip_id == trip_id)
        )
    ).scalar_one()


async def _count_trip_places(db_session, trip_id: UUID) -> int:
    return (
        await db_session.execute(
            select(func.count())
            .select_from(TripPlace)
            .where(TripPlace.trip_id == trip_id)
        )
    ).scalar_one()


async def _seed_owned_trip(
    db_session,
    *,
    n_places: int = 3,
    categories: list[str] | None = None,
    days: int = 1,
    places_per_day: list[int] | None = None,
) -> tuple[User, Destination, list[Place], Trip]:
    """
    Seed an owned trip.

    Single-day: ``n_places`` stops on day 1.
    Multi-day: pass ``places_per_day`` e.g. ``[3, 2]`` (overrides n_places/days).
    """
    user = User(
        email=f"replan-{uuid.uuid4().hex[:8]}@example.com",
        name="Replan Editor",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    dest = Destination(
        name="Replan Test City",
        country="IN",
        display_name="Replan Test City",
        osm_place_id=f"relation/replan-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    if places_per_day is not None:
        per_day = places_per_day
        trip_days = len(per_day)
        total = sum(per_day)
    else:
        per_day = [n_places]
        trip_days = days
        total = n_places

    cats = categories or ["attraction"] * total
    places: list[Place] = []
    for i in range(total):
        place = Place(
            osm_id=f"node/replan-{uuid.uuid4().hex[:8]}",
            name=f"Stop {i}",
            category=cats[i] if i < len(cats) else "attraction",
            tags={},
            enriched_tags=[],
            location=from_shape(Point(88.263 + i * 0.01, 27.041), srid=4326),
            destination_id=dest.id,
        )
        db_session.add(place)
        places.append(place)
    await db_session.flush()

    trip = Trip(
        user_id=user.id,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        destination_id=dest.id,
        days=trip_days,
        preferences={"base_lat": 27.041, "base_lng": 88.263, "interests": []},
        status=TripStatus.COMPLETE,
    )
    db_session.add(trip)
    await db_session.flush()

    idx = 0
    for day_num, count in enumerate(per_day, start=1):
        for order in range(1, count + 1):
            place = places[idx]
            db_session.add(
                TripPlace(
                    trip_id=trip.id,
                    place_id=place.id,
                    day_number=day_num,
                    order_in_day=order,
                    travel_time_min=10,
                    visit_duration_min=60,
                    suggested_start_time=f"{8 + order - 1:02d}:00",
                    polyline=f"old_poly_{idx}",
                )
            )
            idx += 1
    await db_session.commit()

    loaded = await TripService(
        db_session, routing=FakeRoutingProvider()
    ).repo.get_with_places(trip.id)
    assert loaded is not None
    return user, dest, places, loaded


async def _extra_place(
    db_session,
    dest: Destination,
    *,
    category: str = "attraction",
    name: str = "Extra",
) -> Place:
    place = Place(
        osm_id=f"node/replan-extra-{uuid.uuid4().hex[:8]}",
        name=name,
        category=category,
        tags={},
        enriched_tags=[],
        location=from_shape(Point(88.30, 27.05), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.commit()
    return place


@pytest.fixture
def use_fake_routing(monkeypatch):
    fake = FakeRoutingProvider()

    class _PatchedTripService(TripService):
        def __init__(self, session, routing=None):
            super().__init__(session, routing=routing or fake)

    monkeypatch.setattr("src.trips.router.TripService", _PatchedTripService)
    return fake


# ---------------------------------------------------------------------------
# 2.x Service-level matrix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_updates_order_times_and_polylines(db_session) -> None:
    """Scenario 1 — reorder order_in_day + times + polyline."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    new_order = [places[2].id, places[1].id, places[0].id]
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.reorder_stops(trip.id, 1, new_order, user.id, routing=fake)

    day_places = sorted(
        [tp for tp in updated.places if tp.day_number == 1],
        key=lambda tp: tp.order_in_day,
    )
    assert [tp.place_id for tp in day_places] == new_order
    assert all(tp.suggested_start_time for tp in day_places)
    assert all(tp.polyline and tp.polyline.startswith("poly_") for tp in day_places)


@pytest.mark.asyncio
async def test_reorder_preserves_morning_only_mid_list(db_session) -> None:
    """Scenario 2 — preserve-order keeps viewpoint mid-list."""
    user, _dest, places, trip = await _seed_owned_trip(
        db_session,
        n_places=3,
        categories=["attraction", "viewpoint", "attraction"],
    )
    order = [places[0].id, places[1].id, places[2].id]
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.reorder_stops(trip.id, 1, order, user.id, routing=fake)

    day_places = sorted(
        [tp for tp in updated.places if tp.day_number == 1],
        key=lambda tp: tp.order_in_day,
    )
    assert [tp.place_id for tp in day_places] == order
    assert places[1].category == "viewpoint"
    assert day_places[1].place_id == places[1].id


@pytest.mark.asyncio
async def test_remove_stop_reroutes_remaining(db_session) -> None:
    """Scenario 3 — remove_stop; remaining re-routed."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)
    removed = places[1].id

    updated = await svc.remove_stop(trip.id, 1, removed, user.id, routing=fake)

    day_places = [tp for tp in updated.places if tp.day_number == 1]
    assert len(day_places) == 2
    assert removed not in {tp.place_id for tp in day_places}
    assert all(tp.polyline and tp.polyline.startswith("poly_") for tp in day_places)


@pytest.mark.asyncio
async def test_remove_last_stop_day_would_be_empty(db_session) -> None:
    """Scenario 4 — remove last → 422 day_would_be_empty."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=1)
    svc = TripService(db_session, routing=FakeRoutingProvider())

    with pytest.raises(TripEditValidationError) as exc:
        await svc.remove_stop(trip.id, 1, places[0].id, user.id)

    assert exc.value.code == "day_would_be_empty"
    assert await _count_trip_places(db_session, trip.id) == 1
    assert await _count_edit_events(db_session, trip.id) == 0


@pytest.mark.asyncio
async def test_remove_place_not_on_day_404(db_session) -> None:
    """Scenario 5 — stop_not_found_on_day."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    svc = TripService(db_session, routing=FakeRoutingProvider())
    missing = uuid.uuid4()

    with pytest.raises(TripStopNotFoundError) as exc:
        await svc.remove_stop(trip.id, 1, missing, user.id)

    assert exc.value.status_code == 404
    assert exc.value.code == "stop_not_found_on_day"


@pytest.mark.asyncio
async def test_add_stop_creates_place_with_polyline(db_session) -> None:
    """Scenario 6 — add_stop new TripPlace + polyline."""
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    extra = await _extra_place(db_session, dest)
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.add_stop(trip.id, 1, extra.id, user.id, routing=fake)

    day_places = [tp for tp in updated.places if tp.day_number == 1]
    assert len(day_places) == 3
    added = next(tp for tp in day_places if tp.place_id == extra.id)
    assert added.polyline and added.polyline.startswith("poly_")


@pytest.mark.asyncio
async def test_add_duplicate_409(db_session) -> None:
    """Scenario 7 — duplicate → 409."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    svc = TripService(db_session, routing=FakeRoutingProvider())

    with pytest.raises(TripStopConflictError) as exc:
        await svc.add_stop(trip.id, 1, places[0].id, user.id)

    assert exc.value.status_code == 409
    assert exc.value.code == "stop_already_on_trip"


@pytest.mark.asyncio
async def test_add_wrong_destination_422(db_session) -> None:
    """Scenario 8 — wrong destination → 422."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    other_dest = Destination(
        name="Other City",
        country="IN",
        display_name="Other City",
        osm_place_id=f"relation/other-{uuid.uuid4().hex[:8]}",
        lat=28.0,
        lng=77.0,
    )
    db_session.add(other_dest)
    await db_session.flush()
    foreign = Place(
        osm_id=f"node/foreign-{uuid.uuid4().hex[:8]}",
        name="Foreign",
        category="attraction",
        tags={},
        enriched_tags=[],
        location=from_shape(Point(77.0, 28.0), srid=4326),
        destination_id=other_dest.id,
    )
    db_session.add(foreign)
    await db_session.commit()

    svc = TripService(db_session, routing=FakeRoutingProvider())
    with pytest.raises(TripEditValidationError) as exc:
        await svc.add_stop(trip.id, 1, foreign.id, user.id)

    assert exc.value.status_code == 422
    assert "destination" in exc.value.message.lower()


@pytest.mark.asyncio
async def test_add_forces_dropped_stops_422_no_mutation(db_session) -> None:
    """Scenario 9 — edit_would_drop_other_stops; zero place/event changes."""
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    extra = await _extra_place(db_session, dest, name="Dropper")
    before_places = await _count_trip_places(db_session, trip.id)
    before_events = await _count_edit_events(db_session, trip.id)

    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    svc = TripService(db_session, routing=fake)

    with pytest.raises(TripEditValidationError) as exc:
        await svc.add_stop(trip.id, 1, extra.id, user.id, routing=fake)

    assert exc.value.code == "edit_would_drop_other_stops"
    assert await _count_trip_places(db_session, trip.id) == before_places
    assert await _count_edit_events(db_session, trip.id) == before_events


@pytest.mark.asyncio
async def test_reoptimize_day_success(db_session) -> None:
    """Scenario 10 — reoptimize_day success with Fake."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.reoptimize_day(trip.id, 1, user.id, routing=fake)

    day_places = [tp for tp in updated.places if tp.day_number == 1]
    assert len(day_places) == 3
    assert all(tp.polyline and tp.polyline.startswith("poly_") for tp in day_places)


@pytest.mark.asyncio
async def test_reoptimize_forces_dropped_stops_422(db_session) -> None:
    """Scenario 11 — reoptimize drop → same 422 as add."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    before_places = await _count_trip_places(db_session, trip.id)
    before_events = await _count_edit_events(db_session, trip.id)

    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    svc = TripService(db_session, routing=fake)

    with pytest.raises(TripEditValidationError) as exc:
        await svc.reoptimize_day(trip.id, 1, user.id, routing=fake)

    assert exc.value.code == "edit_would_drop_other_stops"
    assert await _count_trip_places(db_session, trip.id) == before_places
    assert await _count_edit_events(db_session, trip.id) == before_events


@pytest.mark.asyncio
async def test_ownership_wrong_user_forbidden(db_session) -> None:
    """Scenario 12 (service) — wrong user → TripForbiddenError."""
    _owner, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    other = User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()

    svc = TripService(db_session, routing=FakeRoutingProvider())
    with pytest.raises(TripForbiddenError):
        await svc.reorder_stops(
            trip.id, 1, [places[1].id, places[0].id], other.id
        )


@pytest.mark.asyncio
async def test_osrm_fallback_none_polyline_succeeds(db_session) -> None:
    """Scenario 13 — None polyline → success (no 500)."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    fake = FakeRoutingProvider(polyline_for=lambda _wps: None)
    svc = TripService(db_session, routing=fake)

    updated = await svc.reoptimize_day(trip.id, 1, user.id, routing=fake)

    day_places = [tp for tp in updated.places if tp.day_number == 1]
    assert len(day_places) == 2
    assert all(tp.suggested_start_time for tp in day_places)
    assert all(tp.polyline is None for tp in day_places)


@pytest.mark.asyncio
async def test_reorder_morning_slot_only_commits(db_session) -> None:
    """Scenario 14 — reorder morning-slot-only → commit (downgrade)."""
    user, _dest, places, trip = await _seed_owned_trip(
        db_session,
        n_places=3,
        categories=["attraction", "attraction", "viewpoint"],
    )
    order = [places[0].id, places[1].id, places[2].id]
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.reorder_stops(trip.id, 1, order, user.id, routing=fake)

    day_places = sorted(
        [tp for tp in updated.places if tp.day_number == 1],
        key=lambda tp: tp.order_in_day,
    )
    assert [tp.place_id for tp in day_places] == order
    assert day_places[2].place_id == places[2].id
    assert await _count_edit_events(db_session, trip.id) == 1


@pytest.mark.asyncio
async def test_non_reorder_morning_slot_still_422(db_session) -> None:
    """Scenario 15 — remove/add/reoptimize morning errors stay hard 422."""
    late_fake = FakeRoutingProvider(duration_for=_late_morning_duration)

    # --- reoptimize ---
    user_r, _d1, places_r, trip_r = await _seed_owned_trip(
        db_session,
        n_places=2,
        categories=["attraction", "viewpoint"],
    )
    svc = TripService(db_session, routing=late_fake)
    with pytest.raises(TripEditValidationError) as exc_reopt:
        await svc.reoptimize_day(trip_r.id, 1, user_r.id, routing=late_fake)
    assert exc_reopt.value.status_code == 422
    errors = (exc_reopt.value.details or {}).get("errors") or []
    assert any("morning_slot_violation" in e for e in errors)
    assert await _count_edit_events(db_session, trip_r.id) == 0

    # --- remove (leave attraction + viewpoint) ---
    user_rm, _d2, places_rm, trip_rm = await _seed_owned_trip(
        db_session,
        n_places=3,
        categories=["attraction", "attraction", "viewpoint"],
    )
    svc2 = TripService(db_session, routing=late_fake)
    with pytest.raises(TripEditValidationError) as exc_rm:
        await svc2.remove_stop(
            trip_rm.id, 1, places_rm[0].id, user_rm.id, routing=late_fake
        )
    assert exc_rm.value.status_code == 422
    errors_rm = (exc_rm.value.details or {}).get("errors") or []
    assert any("morning_slot_violation" in e for e in errors_rm)

    # --- add viewpoint onto attractions ---
    user_a, dest_a, _places_a, trip_a = await _seed_owned_trip(
        db_session, n_places=2, categories=["attraction", "attraction"]
    )
    view = await _extra_place(
        db_session, dest_a, category="viewpoint", name="Late View"
    )
    svc3 = TripService(db_session, routing=late_fake)
    with pytest.raises(TripEditValidationError) as exc_add:
        await svc3.add_stop(trip_a.id, 1, view.id, user_a.id, routing=late_fake)
    assert exc_add.value.status_code == 422
    errors_add = (exc_add.value.details or {}).get("errors") or []
    assert any("morning_slot_violation" in e for e in errors_add)


@pytest.mark.asyncio
async def test_reorder_duplicate_ids_422(db_session) -> None:
    """Scenario 16 — reorder duplicate ids → 422."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    svc = TripService(db_session, routing=FakeRoutingProvider())
    bad = [places[0].id, places[0].id, places[1].id]

    with pytest.raises(TripEditValidationError) as exc:
        await svc.reorder_stops(trip.id, 1, bad, user.id)

    assert exc.value.status_code == 422
    assert await _count_edit_events(db_session, trip.id) == 0


@pytest.mark.asyncio
async def test_successful_edit_exactly_one_trip_edit_event(db_session) -> None:
    """Scenario 17 — exactly one TripEditEvent on success."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)
    assert await _count_edit_events(db_session, trip.id) == 0

    await svc.reorder_stops(
        trip.id,
        1,
        [places[2].id, places[1].id, places[0].id],
        user.id,
        routing=fake,
    )

    events = (
        await db_session.execute(
            select(TripEditEvent).where(TripEditEvent.trip_id == trip.id)
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].edit_type == EditType.REORDER


@pytest.mark.asyncio
async def test_validation_failure_rollback_event_count_unchanged(db_session) -> None:
    """Scenario 18 — failed add → TripEditEvent count unchanged."""
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    extra = await _extra_place(db_session, dest)
    before = await _count_edit_events(db_session, trip.id)
    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    svc = TripService(db_session, routing=fake)

    with pytest.raises(TripEditValidationError):
        await svc.add_stop(trip.id, 1, extra.id, user.id, routing=fake)

    assert await _count_edit_events(db_session, trip.id) == before


@pytest.mark.asyncio
async def test_routing_only_for_mutated_day(db_session) -> None:
    """Scenario 19 — RoutingProvider only sees mutated-day place IDs."""
    user, _dest, places, trip = await _seed_owned_trip(
        db_session, places_per_day=[3, 2]
    )
    day1 = places[:3]
    day2 = places[3:]
    spy = _SpyFake()
    svc = TripService(db_session, routing=spy)

    await svc.reorder_stops(
        trip.id,
        1,
        [day1[2].id, day1[1].id, day1[0].id],
        user.id,
        routing=spy,
    )

    assert spy.call_count >= 1
    assert spy.matrix_place_ids
    seen = set().union(*spy.matrix_place_ids)
    assert set(p.id for p in day1).issubset(seen)
    assert not any(p.id in seen for p in day2)


# ---------------------------------------------------------------------------
# 3.x Thin HTTP — ownership + rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_non_owner_returns_403(client, db_session, use_fake_routing) -> None:
    """Scenario 12 (HTTP) — wrong user → 403."""
    _owner, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    other = User(
        email=f"http-other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()
    token = create_access_token(other.id, other.email)

    response = await client.patch(
        f"/api/v1/trips/{trip.id}/days/1/stops/reorder",
        headers={"Authorization": f"Bearer {token}"},
        json={"place_ids": [str(places[1].id), str(places[0].id)]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_http_rate_limit_over_quota_429(
    client, db_session, use_fake_routing
) -> None:
    """Scenario 20 — mock limiter → 429 on over-quota."""
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}
    url = f"/api/v1/trips/{trip.id}/days/1/stops/reorder"
    body_a = {"place_ids": [str(places[1].id), str(places[0].id)]}
    body_b = {"place_ids": [str(places[0].id), str(places[1].id)]}

    limiter = _TripEditKeyedLimiter(allow_count=1)
    _reset_rate_limiter_for_tests(limiter)
    try:
        ok = await client.patch(url, headers=headers, json=body_a)
        assert ok.status_code == 200, ok.text

        denied = await client.patch(url, headers=headers, json=body_b)
        assert denied.status_code == 429
        assert denied.json()["code"] == "rate_limit_exceeded"
    finally:
        _reset_rate_limiter_for_tests(None)
