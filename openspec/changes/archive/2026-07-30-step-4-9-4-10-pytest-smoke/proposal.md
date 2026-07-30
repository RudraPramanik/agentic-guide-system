## Why

P4.0–4.8 shipped the travel engine, CORS, `OsrmRoutingProvider`, and the tools envelope stub, but P4 cannot close until regression coverage is complete and one offline (plus optional live) end-to-end proof passes. Steps **4.9** and **4.10** in `docs/steps/step4.md` are the phase closeout: deterministic pytest for every locked contract, a fail-fast smoke script without LangGraph, manual verification of the full pipeline, and a `docs/context.md` handoff to P5.

## What Changes

- Fill remaining P4 pytest gaps: `tests/travel_engine/test_travel_rules.py`, `tests/travel_engine/test_purity.py`, and any missing ★ cases from step 4.9 against modules already covered partially in prior batches.
- Keep CI offline: FakeRoutingProvider / mocked `get_route` only in pytest; no live Nominatim/Overpass/OSRM in the suite.
- Add `scripts/test_p4_smoke.py` — sequential, fail-fast offline pipeline (rules → select → allocate → optimize → schedule → validate → unknown tool → purity guard) with optional `OPTIONAL_LIVE_OSRM=1` section.
- Run full `python -m pytest tests/ -v` and the P4 completion checklist (import guards, no TSP package, CORS no wildcard).
- Perform manual / end-to-end feature verification of the P4 pipeline (fixture-driven offline path; optional live OSRM when network available) and record pass/fail against the ship criteria in `docs/steps/step4.md`.
- Update `docs/context.md` **only after** smoke + full pytest pass: mark 4.0–4.10 ✅, set next to P5.1, document MVP SameSite Option A, keep planner graph/tool bodies as stubs.
- No production API or travel_engine algorithm changes unless a test exposes a real contract bug (fix narrowly).

## Capabilities

### New Capabilities

- `p4-verification`: Deterministic P4 pytest coverage, offline smoke script contract, optional live OSRM section, and manual/E2E closeout checklist for steps 4.9–4.10.

### Modified Capabilities

- (none) — module contracts already live under `travel-engine-*`, `cors-middleware`, `planner-routing-provider`, and `planner-tools-envelope`; this change adds verification, not new runtime requirements.

## Impact

- New/extended tests under `tests/travel_engine/`, plus existing `tests/planner/` and `tests/core/test_cors_middleware.py` brought to step 4.9 ★ completeness.
- New script: `scripts/test_p4_smoke.py`.
- Docs: `docs/context.md` after green; step prompt already defines 4.9–4.10 (no step-doc rewrite expected).
- Runtime modules exercised only — no new packages, no LangGraph/SSE/trip HTTP.
- AGENT.md constraints that apply: `travel_engine/` purity (no geo/httpx/LLM/DB); geo only via `src/geo/`; no new packages without `requirements.txt` + why; tests use Fake/mocks for CI.

## Non-goals

- Implementing P5 LangGraph, real tool bodies, `PHASE_TOOLS`, or narrative.
- Implementing P6 trip HTTP, SSE, or Redis-backed caches.
- Making CI depend on live OSRM (optional env flag only).
- Changing cookie `SameSite` code (document Option A in context only).
- Refreshing the full developer manual (cadence is phase end / every 4–5 steps — optional note only if P4 closeout hits that cadence).
