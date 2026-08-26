## 1. V0 — Minimal CI

- [ ] 1.1 Re-read `docs/context.md`, `AGENT.md`, `docs/v2_blueprint.md` (V0–V1), `docs/ci_cd_plan.md` Phase A, and `tests/conftest.py` before coding
- [ ] 1.2 Add `.github/workflows/ci.yml` with triggers on `push`/`pull_request` to `main`; jobs `test` and `docker-build`; no deploy/registry/secrets
- [ ] 1.3 Wire `test` job: Python 3.12, PostGIS service, `DATABASE_URL` (+ minimal Settings env), `pip install -r requirements.txt`, `pytest tests/ -v`
- [ ] 1.4 Wire `docker-build` job: `docker build -f Dockerfile .` only (no push)
- [ ] 1.5 Proof: workflow file present; locally confirm Dockerfile builds (`docker build -f Dockerfile .`) when Docker available

## 2. V1 — query_points migration

- [ ] 2.1 In `src/search/places_index.py`, replace `client.search` with `client.query_points`; map response points → `PlaceSearchResult`; keep destination filter, timeout, and `[]` fail-soft
- [ ] 2.2 Update the three pinned tests in `tests/search/test_places_index.py` to mock/assert `query_points` (error empty, empty-embedding short-circuit, destination filter)
- [ ] 2.3 Proof: `pytest tests/search -v` green
- [ ] 2.4 Proof: `pytest tests/ -v` green (full suite)

## 3. Docs & wrap-up

- [ ] 3.1 Update `docs/context.md` (Last updated, Next step → apply `wire-langfuse-tracing-and-eval-harness` / V2, note V0+V1 done)
- [ ] 3.2 Guardrail check: no new packages; no API/FE contract changes; search fail-soft preserved; litellm/langfuse untouched
