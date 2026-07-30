## 1. Audit and gap-fill P4 pytest (step 4.9)

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step4.md` Steps 4.9–4.10 before coding; map each ★ case to an existing test or a gap.
- [x] 1.2 Create `tests/travel_engine/test_travel_rules.py` covering P2 duration key set, default duration, `CATEGORY_WEIGHTS ⊆ PLACE_TAG_VOCAB`, no `sunrise_point`, no interest-only duration keys.
- [x] 1.3 Create `tests/travel_engine/test_purity.py` that scans `src/travel_engine/**/*.py` for forbidden imports (`src.geo`, `httpx`, `litellm`, `qdrant`, `sqlalchemy`) and asserts zero matches.
- [x] 1.4 Gap-fill existing module tests only where a ★ case is missing (selector / allocator / optimizer / schedule / validator / CORS / planner adapter / execute_tool stub); reuse `tests/travel_engine/fake_routing.py`.
- [x] 1.5 Assert `requirements.txt` has no `tsp` / `ortools` / `python-tsp` (pytest or purity companion check).
- [x] 1.6 Run `python -m pytest tests/travel_engine tests/planner/test_routing_provider.py tests/planner/test_execute_tool_stub.py tests/core/test_cors_middleware.py -v` and fix failures without live network.

## 2. P4 smoke script (step 4.10)

- [x] 2.1 Create `scripts/test_p4_smoke.py` with `_ROOT` sys.path bootstrap, `[OK]`/`[FAIL]` helpers, fail-fast exit 1, and a clear success sentinel.
- [x] 2.2 Implement offline sections 1–8: travel_rules → select_places → allocate_days → optimize_route (Fake) → build_day_schedule → validate_trip (passed) → unknown execute_tool → import purity guard.
- [x] 2.3 Implement optional section 9 gated by `OPTIONAL_LIVE_OSRM=1` (OsrmRoutingProvider pairwise for 3 waypoints); skip when unset.
- [x] 2.4 Run `python scripts/test_p4_smoke.py` offline and confirm exit 0 + success sentinel.

## 3. Full suite and manual / E2E closeout

- [x] 3.1 Run `python -m pytest tests/ -v` (DB `wandr_test` up) and confirm the full suite is green.
- [x] 3.2 Run PowerShell import guard on `src/travel_engine` (`src.geo|httpx|litellm|qdrant|sqlalchemy`) — expect zero matches.
- [x] 3.3 Confirm CORS: `python -c "from src.config import get_settings; s=get_settings(); assert '*' not in s.CORS_ALLOWED_ORIGINS"`.
- [x] 3.4 Optionally run `OPTIONAL_LIVE_OSRM=1 python scripts/test_p4_smoke.py` when network is available; record skip or pass (do not block default closeout on network).
- [x] 3.5 Walk the P4 ship-criteria table in `docs/steps/step4.md` (purity, vocabulary, scoring, route order, drop-retry, schedule, validator, adapter, tools stub, CORS, SameSite doc) and confirm each item has evidence from tests/smoke.

## 4. Record P4 completion

- [x] 4.1 Update `docs/context.md` only after 2.4 + 3.1 green: Last updated, Next step → P5.1, Progress 4.0–4.10 ✅, note `scripts/test_p4_smoke.py`, MVP SameSite Option A, stubs list (travel_engine real; planner graph/tool bodies still stub).
- [x] 4.2 Do not claim P5 complete; do not change auth cookie code.
