"""Offline location golden suite — no planner, LLM, network, or database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evaluation.metrics import location_type_accuracy
from src.geo.schemas import GeocodedPlace
from src.location_intelligence.containment import point_in_search_area
from src.location_intelligence.map_pin import map_pin_location
from src.location_intelligence.resolver import resolve_from_hits
from src.location_intelligence.schemas import (
    ResolvedLocation,
    SearchArea,
    SearchAreaPolicy,
)
from src.location_intelligence.search_area import build_search_area


def _hit(raw: dict[str, Any]) -> GeocodedPlace:
    bbox = raw.get("bounding_box")
    kwargs = {
        "name": raw["name"],
        "display_name": raw.get("display_name") or raw["name"],
        "lat": float(raw["lat"]),
        "lng": float(raw["lng"]),
        "osm_place_id": raw["osm_place_id"],
        "country": raw.get("country") or "XX",
        "addresstype": raw.get("addresstype"),
        "osm_class": raw.get("osm_class"),
        "osm_type_tag": raw.get("osm_type_tag"),
    }
    if isinstance(bbox, list) and len(bbox) == 4:
        kwargs["bbox_west"] = float(bbox[0])
        kwargs["bbox_south"] = float(bbox[1])
        kwargs["bbox_east"] = float(bbox[2])
        kwargs["bbox_north"] = float(bbox[3])
    return GeocodedPlace(**kwargs)


def load_location_cases(folder: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not data.get("id"):
            raise ValueError(f"{path.name}: invalid location case")
        cases.append(data)
    return cases


def score_location_case(case: dict[str, Any]) -> tuple[bool, list[str]]:
    kind = case.get("kind")
    reasons: list[str] = []
    policy = SearchAreaPolicy()

    if kind == "type_accuracy":
        hits = [_hit(h) for h in case.get("geocoder_hits") or []]
        resolution = resolve_from_hits(hits, [], threshold=0.90)
        predicted = [
            c.location_type.value for c in resolution.candidates[:1]
        ] or (
            [resolution.selected.location_type.value]
            if resolution.selected is not None
            else []
        )
        labeled = [str(case["expected_type"])]
        acc = location_type_accuracy(predicted, labeled)
        if acc < 1.0:
            reasons.append(f"type_accuracy={acc}")
        if resolution.status != case.get("expected_status"):
            reasons.append(
                f"status={resolution.status} expected={case.get('expected_status')}"
            )
        return not reasons, reasons

    if kind == "ambiguity":
        hits = [_hit(h) for h in case.get("geocoder_hits") or []]
        resolution = resolve_from_hits(hits, [], threshold=0.90)
        if resolution.status != "ambiguous":
            reasons.append(f"status={resolution.status}")
        if resolution.selected is not None:
            reasons.append("selected_not_null")
        if not resolution.requires_confirmation:
            reasons.append("confirmation_false")
        return not reasons, reasons

    if kind == "map_pin_clamp":
        anchor = map_pin_location(float(case["lat"]), float(case["lng"]))
        area = build_search_area(
            anchor,
            policy,
            user_radius_km=float(case["requested_radius_km"]),
        )
        if area.radius_km != float(case["expected_radius_km"]):
            reasons.append(f"radius={area.radius_km}")
        if area.fallback_used != bool(case.get("expected_fallback_used", False)):
            reasons.append(f"fallback={area.fallback_used}")
        if "clamped" not in area.description.lower() and "clamp" not in area.description.lower():
            # build_search_area says "clamped from"
            if "clamp" not in area.description:
                reasons.append("description_missing_clamp")
        return not reasons, reasons

    if kind == "containment":
        anchor = ResolvedLocation.model_validate(case["anchor"])
        area = SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=float(case["radius_km"]),
            boundary_geojson=None,
            fallback_used=False,
            description="fixture",
        )
        inside = 0
        labeled_inside = 0
        for stop in case.get("stops") or []:
            ok = point_in_search_area(float(stop["lat"]), float(stop["lng"]), area)
            expect = bool(stop["inside"])
            if expect:
                labeled_inside += 1
            if ok == expect:
                if expect:
                    inside += 1
            else:
                reasons.append(f"stop_{stop.get('name')}_mismatch")
        # Containment fraction of selected (inside) stops that are inside.
        if labeled_inside and inside / labeled_inside < 0.98:
            reasons.append("containment_below_0.98")
        return not reasons, reasons

    reasons.append(f"unknown_kind={kind}")
    return False, reasons


def run_location_suite(folder: Path) -> tuple[int, list[str]]:
    cases = load_location_cases(folder)
    if not cases:
        return 1, [f"no cases in {folder}"]
    messages: list[str] = []
    passed = 0
    type_pred: list[str] = []
    type_lab: list[str] = []
    amb_ok = True
    for case in cases:
        ok, reasons = score_location_case(case)
        if ok:
            passed += 1
            messages.append(f"pass {case['id']}")
        else:
            messages.append(f"fail {case['id']}: {', '.join(reasons)}")
        if case.get("kind") == "type_accuracy":
            hits = [_hit(h) for h in case.get("geocoder_hits") or []]
            resolution = resolve_from_hits(hits, [], threshold=0.90)
            if resolution.candidates:
                type_pred.append(resolution.candidates[0].location_type.value)
            type_lab.append(str(case["expected_type"]))
        if case.get("kind") == "ambiguity":
            hits = [_hit(h) for h in case.get("geocoder_hits") or []]
            resolution = resolve_from_hits(hits, [], threshold=0.90)
            if (
                resolution.status != "ambiguous"
                or resolution.selected is not None
                or not resolution.requires_confirmation
            ):
                amb_ok = False
    acc = location_type_accuracy(type_pred, type_lab)
    if acc < 0.95:
        messages.append(f"location_type_accuracy={acc} < 0.95")
        return 1, messages
    if not amb_ok:
        messages.append("ambiguity_gate_failed")
        return 1, messages
    if passed != len(cases):
        return 1, messages
    messages.append(f"ok location_suite cases={len(cases)} type_accuracy={acc:.2f}")
    return 0, messages
