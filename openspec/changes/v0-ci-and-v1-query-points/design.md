## Context

See proposal.md for why. Current code: `search_places` in `src/search/places_index.py` awaits `client.search(...)` inside the existing `asyncio.wait_for` + try/except fail-soft. Three tests in `tests/search/test_places_index.py` mock `mock_client.search`. No `.github/workflows/` exists.

`docs/ci_cd_plan.md` Phase A claims the suite needs no services; that is outdated relative to `tests/conftest.py`, which opens a real PostGIS engine against `…/wandr_test` derived from `DATABASE_URL`. V0 design must include a PostGIS service in CI.

Blueprint SSOT for this slice: `docs/v2_blueprint.md` V0–V1. Follow-on remains `wire-langfuse-tracing-and-eval-harness`.

## Goals / Non-Goals

**Goals:**
- Automated pytest + Dockerfile build gate on main/PRs.
- Zero-behavior `query_points` adapter so later hybrid Prefetch/RRF does not also migrate the deprecated API.
- Keep resilience contracts (timeout, degrade to `[]`) unchanged.

**Non-Goals:**
- CD, registry, golden-eval CI job, hybrid/sparse, Langfuse, `_canonical_text` changes.
- Changing `upsert_*`, `ensure_places_collection`, or collection naming.

## Decisions

### D1 — PostGIS service in the test job (correcting ci_cd_plan)
- **Choice:** GitHub Actions `services:` with a PostGIS image (e.g. `postgis/postgis:16-3.4` or project-equivalent), create/ensure `wandr` DB + grant so conftest can `CREATE EXTENSION` / create `wandr_test` via URL rewrite, set `DATABASE_URL=postgresql+asyncpg://…@localhost:5432/wandr`.
- **Why:** Session-scoped `test_engine` requires live PostGIS; mocking the entire DB harness would rewrite P1–P7 tests.
- **Alternative rejected:** “pytest only modules that don't need DB” — incomplete gate.

### D2 — Python 3.12 + `requirements.txt` for tests; prod Dockerfile for docker-build
- **Choice:** Match Dockerfile `python:3.12-slim`. Test job installs `requirements.txt` (includes pytest + sentence-transformers). Docker job builds `Dockerfile` (uses `requirements-prod.txt` only).
- **Why:** Aligns with `docs/ci_cd_plan.md` Phase A shape and catches prod-dep drift separately from full test deps.
- **Alternative rejected:** Single lockfile consolidation — out of scope.

### D3 — Minimal CI env for Settings
- **Choice:** Set required-looking env in the test job (`SECRET_KEY`, `DATABASE_URL`, dummy `LLM_API_KEY` if settings demand it, empty `REDIS_URL` / Langfuse keys). No GitHub secrets for Phase A.
- **Why:** `get_settings()` loads at import; empty Langfuse keeps NoOp path.
- **Note:** Apply agent verifies against current `Settings` required fields at implement time.

### D4 — `query_points` mapping adapter (local, in places_index)
- **Choice:** Replace `client.search` with `client.query_points(collection_name=…, query=vector, query_filter=…, limit=…)`. Map `response.points` (ScoredPoint-like) → `PlaceSearchResult` the same way today's hit list is mapped. Keep `QDRANT_OPERATION_TIMEOUT_SECONDS` wait_for and existing retry helpers if any wrap this path.
- **Why:** Qdrant client deprecation path; unchanged public function signature.
- **Alternative rejected:** Dual-call fallback search→query_points — unnecessary complexity; suite is mocked and local Qdrant supports query_points.

### D5 — Update exactly three pinned tests
- **Choice:** Mock `query_points`; assert kwargs for filter/limit; empty-embedding asserts `query_points` not awaited.
- **Why:** Blueprint V1.2 explicit; do not broaden test rewrite.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CI fails because wandr_test DB/user missing | Init SQL or first-job step: ensure role/db; document in workflow comments |
| sentence-transformers slows CI install | Accept for Phase A; cache pip later if pain (not this change) |
| `query_points` response shape differs from `search` | Pin mapping in unit test with a fake ScoredPoint payload; manual optional spot-check only |
| ci_cd_plan “no services” drifts from design | Update `docs/context.md` Next step; optional one-line note in ci_cd_plan only if touched — prefer not expanding docs scope beyond context.md |

## Migration Plan

1. Land CI workflow (may be red until V1 tests updated if merged separately — prefer same PR: V0 then V1).
2. Merge V1 code + test mocks; prove `pytest tests/search -v` then full `pytest tests/ -v`.
3. Rollback: revert commit; no DB/Qdrant migrations; collection schema unchanged.

## Open Questions

None material — PostGIS-in-CI is locked by conftest reality.
