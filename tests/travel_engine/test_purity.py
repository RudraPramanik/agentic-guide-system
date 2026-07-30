"""Purity and dependency guards for travel_engine (step 4.9)."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENGINE_DIR = _REPO_ROOT / "src" / "travel_engine"
_REQUIREMENTS = _REPO_ROOT / "requirements.txt"

_FORBIDDEN = re.compile(
    r"src\.geo|import httpx|from httpx|litellm|qdrant|sqlalchemy",
    re.IGNORECASE,
)
_TSP = re.compile(r"tsp|ortools|python-tsp", re.IGNORECASE)


def test_travel_engine_has_no_forbidden_imports() -> None:
    hits: list[str] = []
    for path in sorted(_ENGINE_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN.search(line):
                hits.append(f"{path.relative_to(_REPO_ROOT)}:{i}: {line.strip()}")
    assert hits == [], "forbidden imports in travel_engine:\n" + "\n".join(hits)


def test_requirements_have_no_tsp_solver() -> None:
    text = _REQUIREMENTS.read_text(encoding="utf-8")
    hits = [
        f"line {i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if _TSP.search(line)
    ]
    assert hits == [], "TSP solver packages must not be in requirements:\n" + "\n".join(
        hits
    )
