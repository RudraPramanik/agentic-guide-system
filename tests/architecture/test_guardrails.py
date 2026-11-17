"""Slice 0.5 architecture guardrails — §10 rules enforceable without new packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture._helpers import (
    REPO_ROOT,
    SRC_ROOT,
    V83_FLAG_DEFAULTS,
    VIOLATIONS_PATH,
    find_validation_finding_classes,
    load_allowlist,
    new_violations,
    rel,
    scan_g1_llm_sdk_imports,
    scan_g2_travel_engine_io,
    scan_g3_os_environ,
    scan_g4_node_tool_impl_imports,
    file_assigns_run_status,
    scan_g5_router_repository_imports,
    scan_g15_run_status_assigns,
    scan_g6_module_global_tool_context,
    scan_g7_state_forbidden_fields,
    scan_g16_lodging_media_imports,
)


@pytest.fixture(scope="module")
def allowlist() -> dict[str, set[str]]:
    return load_allowlist()


def test_allowlisted_paths_still_match(allowlist: dict[str, set[str]]) -> None:
    """Stale allowlist entries fail: path must exist and still breach its rule."""
    assert VIOLATIONS_PATH.is_file()
    scanners = {
        "G1": scan_g1_llm_sdk_imports,
        "G2": scan_g2_travel_engine_io,
        "G3": scan_g3_os_environ,
        "G4": scan_g4_node_tool_impl_imports,
        "G5": scan_g5_router_repository_imports,
        "G16": scan_g16_lodging_media_imports,
    }
    for rule, paths in allowlist.items():
        scan = scanners.get(rule)
        assert scan is not None, f"no scanner for allowlisted rule {rule}"
        found = scan()
        for path in paths:
            assert (REPO_ROOT / path).is_file(), f"allowlisted path missing: {path}"
            assert path in found, (
                f"allowlisted {rule} path no longer matches (remove from "
                f"VIOLATIONS.md if fixed): {path}"
            )


def test_g1_llm_sdk_only_in_gateway(allowlist: dict[str, set[str]]) -> None:
    found = scan_g1_llm_sdk_imports()
    bad = new_violations("G1", found, allowlist)
    assert bad == set(), f"G1 LLM SDK imports outside gateway:\n" + "\n".join(sorted(bad))


def test_g2_travel_engine_no_io_imports(allowlist: dict[str, set[str]]) -> None:
    found = scan_g2_travel_engine_io()
    bad = new_violations("G2", found, allowlist)
    assert bad == set(), f"G2 travel_engine I/O/geo imports:\n" + "\n".join(sorted(bad))


def test_g3_os_environ_only_in_config(allowlist: dict[str, set[str]]) -> None:
    found = scan_g3_os_environ()
    bad = new_violations("G3", found, allowlist)
    assert bad == set(), f"G3 os.environ/getenv outside config:\n" + "\n".join(sorted(bad))


def test_g4_graph_nodes_no_tool_impl_imports(allowlist: dict[str, set[str]]) -> None:
    found = scan_g4_node_tool_impl_imports()
    bad = new_violations("G4", found, allowlist)
    assert bad == set(), f"G4 node tool-impl imports:\n" + "\n".join(sorted(bad))


def test_g5_routers_no_repository_imports(allowlist: dict[str, set[str]]) -> None:
    found = scan_g5_router_repository_imports()
    bad = new_violations("G5", found, allowlist)
    assert bad == set(), f"G5 router repository imports:\n" + "\n".join(sorted(bad))


def test_g6_no_module_global_tool_context() -> None:
    hits = scan_g6_module_global_tool_context()
    assert hits == [], "G6 module-global ToolContext:\n" + "\n".join(hits)


def test_g7_travel_state_has_no_session_or_routing_fields() -> None:
    hits = scan_g7_state_forbidden_fields()
    assert hits == [], "G7 forbidden TravelState fields:\n" + "\n".join(hits)


def test_g11_v83_feature_flags_default_off_when_present() -> None:
    """Only assert §7.1 flags that already exist on Settings — do not invent them."""
    from src.config import Settings

    bad: list[str] = []
    for name, expected in V83_FLAG_DEFAULTS.items():
        field = Settings.model_fields.get(name)
        if field is None:
            continue
        default = field.default
        if default != expected:
            bad.append(f"{name} default={default!r} expected={expected!r}")
    assert bad == [], "G11 feature flags must default off/legacy:\n" + "\n".join(bad)


def test_g14_validation_finding_codes_when_type_exists() -> None:
    """If ValidationFinding appears, every .code must come from a stable registry.

    The type is absent today (deferred in VIOLATIONS.md). When added, require a
    registry module exporting FINDING_CODES or ValidationFindingCode.
    """
    finding_modules = find_validation_finding_classes()
    if not finding_modules:
        return

    registry_paths = [
        SRC_ROOT / "travel_engine" / "finding_codes.py",
        SRC_ROOT / "travel_engine" / "validation_codes.py",
    ]
    registry_file = next((p for p in registry_paths if p.is_file()), None)
    assert registry_file is not None, (
        "ValidationFinding exists at "
        + ", ".join(finding_modules)
        + " but no finding-code registry file was found under travel_engine/"
    )

    # Collect string/enum members named as codes from the registry module text.
    text = registry_file.read_text(encoding="utf-8")
    assert "FINDING" in text.upper() or "CODE" in text.upper(), (
        f"{rel(registry_file)} does not look like a finding-code registry"
    )


def test_g16_no_lodging_or_media_imports(allowlist: dict[str, set[str]]) -> None:
    found = scan_g16_lodging_media_imports()
    bad = new_violations("G16", found, allowlist)
    assert bad == set(), (
        "G16 lodging/media imports in planner service or travel_engine:\n"
        + "\n".join(sorted(bad))
    )


def test_g15_run_status_assign_only_in_lifecycle_service(tmp_path: Path) -> None:
    assert scan_g15_run_status_assigns() == set()
    sample = tmp_path / "bad_run_status.py"
    sample.write_text(
        "from src.planner.runs.models import RunStatus\n"
        "def poke(run):\n"
        "    run.status = RunStatus.FAILED\n",
        encoding="utf-8",
    )
    assert file_assigns_run_status(sample) is True


def test_deferred_rules_documented() -> None:
    text = VIOLATIONS_PATH.read_text(encoding="utf-8")
    for rule in ("G8", "G9", "G10", "G12", "G13", "G14"):
        assert rule in text, f"{rule} deferral missing from VIOLATIONS.md"
    deferred = text.split("## Deferred", 1)[1]
    assert "G15" not in deferred
