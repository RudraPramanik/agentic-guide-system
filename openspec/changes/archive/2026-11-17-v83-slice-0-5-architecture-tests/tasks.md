## 1. Preflight

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 row 0.5 and §10, this change's `design.md`, and both delta specs. Confirm writes are only under `tests/architecture/**` and `.github/workflows/ci.yml`. Do not edit `docs/context.md` (allowed-path conflict with the OpenSpec context-update rule).
- [x] 1.2 Scan the current tree for G1–G5 breaches. Record every hit (expected: G3 in `src/core/observability/tracing.py`). Do not edit `src/`.

## 2. Harness and allowlist

- [x] 2.1 Add `tests/architecture/` helpers that walk `src/**/*.py` with stdlib `ast` / text checks and load allowlisted paths per rule id from `VIOLATIONS.md`.
- [x] 2.2 Add `tests/architecture/VIOLATIONS.md` with the preflight G3 entry for `src/core/observability/tracing.py`, plus a short deferral note for G8/G9/G10/G12/G13/G15 (owned elsewhere or not yet present). Assert allowlisted paths still exist and still match.

## 3. Guardrail tests

- [x] 3.1 Add tests for G1 (LLM SDK imports only in `src/core/llm/client.py`) and G2 (`travel_engine` has no forbidden I/O/geo imports).
- [x] 3.2 Add tests for G3 (`os.environ` / `os.getenv` only in `src/config.py`, minus the G3 allowlist) and G4 (graph nodes do not import concrete tool impl modules).
- [x] 3.3 Add tests for G5 (routers do not import repositories; `get_db` / `AsyncSession` Depends allowed).
- [x] 3.4 Add tests for G7 (graph TypedDict state has no `AsyncSession` / `RoutingProvider` fields), G11 (documented feature flags default off/legacy), G14 (`ValidationFinding.code` values are in the stable registry — locate the existing registry or halt), and G16 (no lodging client / `src.geo.media` imports from planner service or `travel_engine`). Optionally add the cheap G6 static check (no module-global `ToolContext`).

## 4. CI and verify

- [x] 4.1 Update `.github/workflows/ci.yml` so the `test` job runs `pytest tests/architecture -v` explicitly, in addition to `pytest tests/ -v`.
- [x] 4.2 Run `pytest tests/architecture -v` and confirm exit 0 with the allowlist in place. Do not clear violations by editing `src/`.
