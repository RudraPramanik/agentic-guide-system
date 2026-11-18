"""Ingestion quality report for checked-in samples. Not a live catalog dump.

Reads evals/fixtures/ingestion/{darjeeling,manali,goa}.json and prints JSON.
Does not open a database or the network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.destinations.ingestion_report import load_fixture_dir  # noqa: E402


def main() -> int:
    folder = ROOT / "evals" / "fixtures" / "ingestion"
    try:
        report = load_fixture_dir(folder)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
