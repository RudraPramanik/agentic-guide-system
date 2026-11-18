"""Engine must not import location intelligence; planner may."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"


def _scan(root: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8-sig")
        if "LOCATION_V2_ENABLED" in text or "src.location_intelligence" in text:
            hits.append(path.relative_to(REPO).as_posix())
        if "from src import location_intelligence" in text:
            hits.append(path.relative_to(REPO).as_posix())
    return hits


def test_engine_ignores_location_v2() -> None:
    hits = _scan(SRC / "travel_engine")
    assert hits == [], f"unexpected references: {hits}"


def test_area_respect_is_active() -> None:
    path = REPO / "tests" / "travel_engine" / "test_properties.py"
    text = path.read_text(encoding="utf-8-sig")
    assert '@pytest.mark.skip(reason="slice 3 owns SearchArea")' not in text
    assert "def test_area_respect" in text
