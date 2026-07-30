## Context

P4.0–4.8 are implemented: pure `travel_engine/*`, CORS middleware, `OsrmRoutingProvider`, and `ToolResult`/`execute_tool` stub. Prior batches already added substantial pytest under `tests/travel_engine/` (selector, allocator, optimizer, schedule, validator), `tests/planner/`, and `tests/core/test_cors_middleware.py`, plus `tests/travel_engine/fake_routing.py`.

Gaps vs `docs/steps/step4.md` steps **4.9–4.10**:

| Gap | Status |
|-----|--------|
| `tests/travel_engine/test_travel_rules.py` | Missing |
| `tests/travel_engine/test_purity.py` | Missing |
| ★ case audit vs existing modules | Partial — fill only what’s missing |
| `scripts/test_p4_smoke.py` | Missing |
| Manual / E2E feature checklist run | Not done |
| `docs/context.md` P4 closeout | Blocked until green |

Canonical contract: `docs/steps/step4.md` Steps 4.9–4.10 and the P4 Complete checklist. No LangGraph.

## Goals / Non-Goals

**Goals:**

- Complete deterministic P4 pytest covering every ★ case in step 4.9.
- Provide one offline fail-fast smoke command that exercises the full engine pipeline with FakeRoutingProvider.
- Support optional live OSRM via `OPTIONAL_LIVE_OSRM=1` without making CI depend on it.
- Run a documented manual/E2E verification pass against the P4 ship criteria.
- Record P4 complete in `docs/context.md` only after full pytest + default smoke pass; set next step to P5.1 and document SameSite Option A.

**Non-Goals:**

- Changing travel_engine algorithms, CORS behavior, or adapter APIs (except narrow bugfixes proven by failing tests).
- P5 tool bodies / LangGraph / SSE / trip HTTP.
- Live geo in pytest.
- Developer-manual full rewrite (unless cadence rules explicitly trigger at P4 close — prefer a light note only).

## Decisions

### 1. Gap-fill pytest, don’t rewrite existing suites

Audit step 4.9 ★ cases against current tests. Add `test_travel_rules.py` and `test_purity.py`; extend existing files only where a ★ case is absent. Reuse `FakeRoutingProvider` from `tests/travel_engine/fake_routing.py`.

Alternative considered: consolidate all P4 tests into one file. Rejected — module-scoped files already match prior batches and step 4.9’s file list.

### 2. Offline smoke by default; live OSRM opt-in

Mirror P2’s fail-fast section style (`[OK]`/`[FAIL]`, exit 1 on first failure) but keep the default path network-free:

1. travel_rules constants  
2. select_places fixture  
3. allocate_days  
4. optimize_route + FakeRoutingProvider  
5. build_day_schedule  
6. validate_trip (expect passed on good plan)  
7. execute_tool unknown → ok=False  
8. import guard (travel_engine has no geo/httpx/litellm/qdrant)  
9. OPTIONAL_LIVE_OSRM — skip unless env set; if set, pairwise 3 waypoints via OsrmRoutingProvider

Alternative considered: always hit public OSRM. Rejected — breaks offline/dev without network and differs from step 4.10 FAILURE BOUNDARY.

### 3. Manual/E2E = ship-criteria checklist, not a second harness

Manual testing means: run the P4 Complete checklist from step4.md (pytest, smoke, PowerShell import/TSP/CORS guards), plus optionally the live OSRM smoke section. Record outcomes in the apply session; do not invent a second framework or UI. Feature “E2E” here is the in-process engine pipeline (rules→…→validate), not HTTP trip generation (P6).

Alternative considered: ASGI smoke against planner endpoints. Rejected — no planner HTTP yet.

### 4. Context.md update is last and gated

Update `docs/context.md` only after:

1. `python -m pytest tests/ -v` green  
2. `python scripts/test_p4_smoke.py` green (offline)  
3. Import/TSP/CORS guards from the checklist  

Content: Progress 4.0–4.10 ✅; Next = P5.1; Implemented modules for any missing smoke script row; Stubs — remove “travel_engine stubs”, keep planner graph/tool bodies; Deployment Option A SameSite=Lax note.

### 5. No new packages; purity via AST/string scan

Purity test scans `src/travel_engine/**/*.py` for forbidden imports (`src.geo`, `httpx`, `litellm`, `qdrant`, `sqlalchemy`). Smoke section 8 repeats the same invariant. Assert `requirements.txt` has no `tsp`/`ortools`/`python-tsp`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Existing tests already cover most ★ cases → duplicate noise | Audit first; add only gaps |
| Optional live OSRM flaky when env set | Section-scoped fail; default smoke ignores it |
| Premature context.md update | Explicit gate: smoke + full pytest first |
| Contract bug found in engine | Narrow production fix + test; do not expand scope to P5 |
| Manual checklist skipped | tasks.md includes explicit checklist items with evidence |

## Migration Plan

N/A for schema/API. Rollout = merge tests + smoke + context update. Rollback = revert those files; production runtime unchanged if no bugfix.

## Open Questions

None — step 4.9–4.10 locks are sufficient. If a ★ case conflicts with an earlier OpenSpec lock, prefer `docs/steps/step4.md` + `docs/blueprint_final.md` v6.1 and ask the user only on true contradiction.
