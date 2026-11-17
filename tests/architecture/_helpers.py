"""AST/text helpers for Slice 0.5 architecture guardrails."""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
VIOLATIONS_PATH = Path(__file__).resolve().parent / "VIOLATIONS.md"

_LLM_SDKS = frozenset({"litellm", "groq", "openai"})
_TE_FORBIDDEN_TOP = frozenset(
    {"httpx", "sqlalchemy", "qdrant_client", "litellm", "requests", "redis", "aiohttp"}
)
_G4_ALLOWED_TOOL_MODULES = frozenset({"registry", "schemas"})
_ENV_USE = re.compile(r"\bos\.environ\b|\bos\.getenv\b")

# Blueprint §7.1 flags — only assert defaults when the field exists on Settings.
V83_FLAG_DEFAULTS: dict[str, object] = {
    "RUN_TRACKING_ENABLED": False,
    "LOCATION_V2_ENABLED": False,
    "TRAVEL_ENGINE_V2_ENABLED": False,
    "VALIDATOR_V2_ENFORCE": False,
    "READINESS_V2_ENABLED": False,
    "CANONICAL_TRIP_V2_ENABLED": False,
    "REASONING_LAYER_ENABLED": False,
    "REASONING_SHADOW_SAMPLE_RATE": 0.0,
    "EVALUATION_JUDGE_ENABLED": False,
    "LODGING_V1_ENABLED": False,
    "MEDIA_ENRICH_ENABLED": False,
}


def iter_src_py(*, under: Path | None = None) -> list[Path]:
    root = under if under is not None else SRC_ROOT
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_allowlist(path: Path = VIOLATIONS_PATH) -> dict[str, set[str]]:
    """Parse `| Rule | Path | Note |` rows from the Allowlist section."""
    text = path.read_text(encoding="utf-8")
    section = text.split("## Deferred", 1)[0]
    out: dict[str, set[str]] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        rule, file_path = cells[0], cells[1]
        if rule.lower() == "rule" or set(rule) <= {"-", ":"}:
            continue
        out.setdefault(rule, set()).add(file_path.replace("\\", "/"))
    return out


def new_violations(rule: str, found: set[str], allowlist: dict[str, set[str]]) -> set[str]:
    return found - allowlist.get(rule, set())


def read_src_text(path: Path) -> str:
    """Read source text; utf-8-sig strips a BOM some files still carry."""
    return path.read_text(encoding="utf-8-sig")


def parse_tree(path: Path) -> ast.AST | None:
    try:
        return ast.parse(read_src_text(path), filename=str(path))
    except SyntaxError:
        return None


def import_module_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def module_is_geo(name: str) -> bool:
    parts = name.split(".")
    if parts[0] == "geo":
        return True
    if "geo" in parts:
        return True
    return name.startswith("src.geo")


def scan_g1_llm_sdk_imports() -> set[str]:
    allowed = (SRC_ROOT / "core" / "llm" / "client.py").resolve()
    hits: set[str] = set()
    for path in iter_src_py():
        if path.resolve() == allowed:
            continue
        tree = parse_tree(path)
        if tree is None:
            continue
        for name in import_module_names(tree):
            top = name.split(".")[0]
            if top in _LLM_SDKS:
                hits.add(rel(path))
                break
    return hits


def scan_g2_travel_engine_io() -> set[str]:
    hits: set[str] = set()
    engine = SRC_ROOT / "travel_engine"
    for path in iter_src_py(under=engine):
        tree = parse_tree(path)
        if tree is None:
            continue
        for name in import_module_names(tree):
            top = name.split(".")[0]
            if top in _TE_FORBIDDEN_TOP or module_is_geo(name):
                hits.add(rel(path))
                break
    return hits


def scan_g3_os_environ() -> set[str]:
    allowed = rel(SRC_ROOT / "config.py")
    hits: set[str] = set()
    for path in iter_src_py():
        text = read_src_text(path)
        if _ENV_USE.search(text):
            r = rel(path)
            if r != allowed:
                hits.add(r)
    return hits


def scan_g4_node_tool_impl_imports() -> set[str]:
    hits: set[str] = set()
    nodes = SRC_ROOT / "planner" / "graph" / "nodes"
    if not nodes.is_dir():
        return hits
    for path in iter_src_py(under=nodes):
        tree = parse_tree(path)
        if tree is None:
            continue
        for name in import_module_names(tree):
            if name == "src.planner.tools" or name.startswith("src.planner.tools."):
                rest = name[len("src.planner.tools") :].lstrip(".")
                first = rest.split(".")[0] if rest else ""
                # Bare package import pulls concrete tools via __init__ — forbid.
                if first == "" or first not in _G4_ALLOWED_TOOL_MODULES:
                    hits.add(rel(path))
                    break
    return hits


def _references_run_status(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {"PlannerRun", "RunStatus"}:
            return True
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in {"PlannerRun", "RunStatus"}:
                    return True
                if alias.asname in {"PlannerRun", "RunStatus"}:
                    return True
    return False


def _assigns_status_attr(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr == "status":
                return True
    return False


def file_assigns_run_status(path: Path) -> bool:
    """True when the file both names the run model and stores ``.status``."""
    tree = parse_tree(path)
    if tree is None:
        return False
    return _references_run_status(tree) and _assigns_status_attr(tree)


def scan_g15_run_status_assigns() -> set[str]:
    allowed = rel(SRC_ROOT / "planner" / "runs" / "service.py")
    hits: set[str] = set()
    for path in iter_src_py():
        if rel(path) == allowed:
            continue
        if file_assigns_run_status(path):
            hits.add(rel(path))
    return hits


def scan_g5_router_repository_imports() -> set[str]:
    hits: set[str] = set()
    for path in iter_src_py():
        # Domain routers are named router.py in this repo.
        if path.name != "router.py":
            continue
        tree = parse_tree(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
                mods.extend(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
            blob = " ".join(mods)
            if re.search(r"repository|BaseRepository", blob, re.IGNORECASE):
                hits.add(rel(path))
                break
    return hits


def scan_g7_state_forbidden_fields() -> list[str]:
    """Return human-readable hits if TravelState declares forbidden field types."""
    state_path = SRC_ROOT / "planner" / "graph" / "state.py"
    if not state_path.is_file():
        return ["missing src/planner/graph/state.py"]
    tree = parse_tree(state_path)
    if tree is None:
        return ["unparseable src/planner/graph/state.py"]
    forbidden = {"AsyncSession", "RoutingProvider", "ToolContext"}
    hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TravelState":
            for item in node.body:
                if not isinstance(item, ast.AnnAssign) or not isinstance(
                    item.target, ast.Name
                ):
                    continue
                ann = ast.dump(item.annotation)
                for name in forbidden:
                    if name in ann:
                        hits.append(f"TravelState.{item.target.id} uses {name}")
    return hits


def scan_g6_module_global_tool_context() -> list[str]:
    hits: list[str] = []
    graph = SRC_ROOT / "planner" / "graph"
    if not graph.is_dir():
        return hits
    for path in iter_src_py(under=graph):
        tree = parse_tree(path)
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and "tool_context" in target.id.lower():
                        hits.append(f"{rel(path)}: module-level {target.id}")
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                ann = ast.dump(node.annotation) if node.annotation else ""
                if "ToolContext" in ann or "tool_context" in node.target.id.lower():
                    hits.append(f"{rel(path)}: module-level {node.target.id}")
    return hits


def scan_g16_lodging_media_imports() -> set[str]:
    targets = [SRC_ROOT / "planner" / "service.py"]
    engine = SRC_ROOT / "travel_engine"
    if engine.is_dir():
        targets.extend(iter_src_py(under=engine))
    hits: set[str] = set()
    for path in targets:
        if not path.is_file():
            continue
        tree = parse_tree(path)
        if tree is None:
            continue
        for name in import_module_names(tree):
            lower = name.lower()
            if "lodging" in lower or name.startswith("src.geo.media") or ".geo.media" in name:
                hits.add(rel(path))
                break
    return hits


def find_validation_finding_classes() -> list[str]:
    found: list[str] = []
    for path in iter_src_py():
        tree = parse_tree(path)
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "ValidationFinding":
                found.append(rel(path))
    return found
