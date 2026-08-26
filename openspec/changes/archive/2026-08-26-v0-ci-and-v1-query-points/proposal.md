## Why

v7 work (`docs/v2_blueprint.md` V2+) assumes an automated pytest gate and a non-deprecated Qdrant query path. Neither exists today: no `.github/workflows/`, and `search_places` still calls `AsyncQdrantClient.search` (three pinned tests mock that API). Landing V0 + V1 first de-risks every later proof and keeps hybrid/Langfuse changes from fighting a deprecated client.

## What Changes

- **V0 — Minimal CI (Phase A):** add `.github/workflows/ci.yml` with `pytest tests/ -v` and `docker build -f Dockerfile .` on push/PR to `main`. No secrets, no deploy, no registry push (`docs/ci_cd_plan.md` Phase A).
- **V1 — `query_points` migration:** in `src/search/places_index.py`, replace `client.search` with `client.query_points`; map `QueryResponse.points[]` → existing `PlaceSearchResult`. Preserve destination filter, tenacity/timeouts, and `[]` on Qdrant errors.
- **V1 tests:** update the three pinned search tests to mock `query_points` instead of `search`.
- **Docs checkpoint:** update `docs/context.md` after validated proofs (Next step → V2 / Langfuse change).

No **BREAKING** API/FE changes. Ranking and HTTP envelopes stay identical.

## Capabilities

### New Capabilities

- `github-actions-ci`: Minimal GitHub Actions CI gate — pytest + prod Dockerfile build; no deploy.

### Modified Capabilities

- `p3-place-knowledge-layer`: Destination-scoped `search_places` MUST use the current Qdrant query API (`query_points`) while keeping the same fail-soft contracts and `PlaceSearchResult` shape.

## Impact

- **Code:** `src/search/places_index.py`; `tests/search/test_places_index.py`.
- **Ops:** `.github/workflows/ci.yml` (new).
- **Docs:** `docs/context.md` (checkpoint only).
- **APIs / FE:** none — planner `search_places` tool still consumes `place_id` only.
- **Dependencies:** none new.
- **Follow-on (explicitly out of this change):** `wire-langfuse-tracing-and-eval-harness` (V2–V3), then hybrid / `places_v2` (V4–V5).

## Non-goals

- Full CD / registry push / auto-deploy (`docs/ci_cd_plan.md` Phase B).
- Golden eval job in CI (hook only after V3 lands).
- Sparse/hybrid search, `places_v2`, Langfuse wiring, `_canonical_text` expansion.
- Changing upsert / collection ensure / embedding backends.
