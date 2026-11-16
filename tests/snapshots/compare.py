"""Load checked-in JSON fixtures and compare normalized bodies. No update switch."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from tests.snapshots.normalize import normalize

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "snapshots"


def load_request(name: str) -> Any:
    path = FIXTURES / "requests" / name
    return json.loads(path.read_text(encoding="utf-8"))


def assert_fixture(name: str, payload: Any) -> None:
    path = FIXTURES / name
    if not path.is_file():
        raise AssertionError(f"missing fixture {path}")
    actual = normalize(payload)
    expected = json.loads(path.read_text(encoding="utf-8"))
    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                json.dumps(expected, indent=2).splitlines(),
                json.dumps(actual, indent=2).splitlines(),
                fromfile="fixture",
                tofile="actual",
                lineterm="",
            )
        )
        raise AssertionError(f"{name} drifted\n{diff}")
