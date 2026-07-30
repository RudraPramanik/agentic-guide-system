## Purpose

P4 verification closeout — deterministic pytest for the travel engine, CORS, planner adapter/envelope, and purity; offline fail-fast `scripts/test_p4_smoke.py`; optional live OSRM; manual/E2E ship-criteria verification; and the rule that P4 completion is recorded in `docs/context.md` only after both full pytest and default smoke pass.

## ADDED Requirements

### Requirement: P4 pytest covers travel_rules and purity
The project SHALL provide `tests/travel_engine/test_travel_rules.py` and `tests/travel_engine/test_purity.py`. Rules tests MUST assert structural duration keys cover the P2 category set, unknown categories use `VISIT_DURATION_DEFAULT_MIN`, `CATEGORY_WEIGHTS` keys are a subset of `PLACE_TAG_VOCAB`, and `sunrise_point` is absent from morning-only config. Purity tests MUST fail if any file under `src/travel_engine/` imports `src.geo`, `httpx`, `litellm`, `qdrant`, or `sqlalchemy`.

#### Scenario: Duration map covers P2 categories and default
- **WHEN** `VISIT_DURATION_BY_CATEGORY` and `visit_duration_min` are inspected
- **THEN** keys include `museum`, `viewpoint`, `monastery`, `attraction`, `park`, and `trailhead`, and `visit_duration_min("unknown_future")` equals the default duration

#### Scenario: Interest weights stay inside PLACE_TAG_VOCAB
- **WHEN** `CATEGORY_WEIGHTS` keys are compared to `PLACE_TAG_VOCAB`
- **THEN** every weight key is a member of the vocab and interest-only tags such as `trek` are not duration-map keys

#### Scenario: travel_engine purity scan
- **WHEN** all Python files under `src/travel_engine/` are scanned for forbidden import patterns
- **THEN** there are zero matches for `src.geo`, `httpx`, `litellm`, `qdrant`, and `sqlalchemy`

### Requirement: P4 pytest covers engine pipeline contracts
The project SHALL keep or extend module tests so every step 4.9 ★ case is covered: selector (multi-interest outranks single; empty tags score 0; avoid-same-day drops lower), allocator (18 places / 3 days within caps; `days=0` → `ValueError`), optimizer (Fake optimal order; over-budget → `dropped_stops` with reason; no TSP package in requirements), schedule (6-stop day; viewpoint in slots 1–2; start ≥ `08:00`; lunch gap when spanning `13:00`), and validator (good fixture empty errors; repeat place; late viewpoint; `empty_itinerary`).

#### Scenario: Focused P4 pytest package is green
- **WHEN** `python -m pytest tests/travel_engine tests/planner/test_routing_provider.py tests/planner/test_execute_tool_stub.py tests/core/test_cors_middleware.py -v` is run
- **THEN** all tests pass without live network access

#### Scenario: Full suite remains green
- **WHEN** `python -m pytest tests/ -v` is run with the test database available
- **THEN** the complete suite passes and failing P4 tests block any claim of P4 completion

### Requirement: P4 CORS and planner stub tests remain deterministic
The project SHALL retain CORS tests that assert a configured origin is echoed and settings never include `*` with credentialed CORS design, planner tests that mock `get_route` for pairwise matrix and `used_fallback` mapping, and `execute_tool` unknown-name soft failure (`ok=False`, never raise).

#### Scenario: CORS configured origin echoed
- **WHEN** a TestClient request includes `Origin: http://localhost:3000` (or the configured allowlist origin)
- **THEN** the response includes `Access-Control-Allow-Origin` echoing that origin and settings contain no `*`

#### Scenario: Unknown tool soft-fails
- **WHEN** `execute_tool` is called with a name absent from the P4 registry
- **THEN** it returns `ToolResult(ok=False)` and does not raise

### Requirement: P4 smoke script proves the offline pipeline
The project SHALL provide `scripts/test_p4_smoke.py` that prints clear section headers, uses `[OK]`/`[FAIL]` markers, exits non-zero on the first failed section, and never prints an overall PASS if any section failed. Default run MUST succeed offline using FakeRoutingProvider. Sections MUST cover travel_rules, select_places, allocate_days, optimize_route, build_day_schedule, validate_trip (passed on constructed good plan), unknown `execute_tool`, and travel_engine import purity.

#### Scenario: Default smoke passes offline
- **WHEN** `python scripts/test_p4_smoke.py` is run without `OPTIONAL_LIVE_OSRM`
- **THEN** every required section prints `[OK]` and the process exits 0 with a clear success sentinel

#### Scenario: Smoke fails loud by section
- **WHEN** any section invariant fails
- **THEN** the script prints `[FAIL]` with the section name and exits non-zero without claiming overall PASS

### Requirement: Optional live OSRM smoke is gated by env
When `OPTIONAL_LIVE_OSRM=1` is set, the smoke script SHALL run an additional section that builds a pairwise matrix for three waypoints via `OsrmRoutingProvider`. When the env var is unset, that section MUST be skipped. Network failure during the optional section MUST NOT make the default (env unset) run fail.

#### Scenario: Live OSRM section skipped by default
- **WHEN** the smoke script runs without `OPTIONAL_LIVE_OSRM=1`
- **THEN** the live OSRM section is skipped and the default run can still PASS

#### Scenario: Live OSRM section exercises adapter
- **WHEN** `OPTIONAL_LIVE_OSRM=1` is set and the section runs
- **THEN** `OsrmRoutingProvider.travel_matrix` returns a full directed pairwise set for three waypoints (fallback legs allowed)

### Requirement: Manual and E2E closeout follows the P4 ship checklist
Before recording P4 complete, the implementer MUST execute the P4 Complete verification checklist from `docs/steps/step4.md`: full pytest, default smoke, PowerShell import guard on `src/travel_engine`, no TSP package in `requirements.txt`, and CORS settings without `*`. Manual/E2E feature verification means this checklist plus confirming the offline pipeline constructs a `validate_trip`–passing itinerary; it MUST NOT require planner HTTP or LangGraph (those are stubs / future phases).

#### Scenario: Ship criteria gates context update
- **WHEN** any checklist item fails
- **THEN** `docs/context.md` MUST NOT mark steps 4.0–4.10 done or claim P4 complete

#### Scenario: Context records P4 handoff after green
- **WHEN** full pytest and default smoke have passed and the checklist is green
- **THEN** `docs/context.md` marks 4.0–4.10 ✅, sets next step to P5.1, documents MVP SameSite Option A (same registrable domain; cookies stay Lax), lists the P4 smoke script, and keeps planner graph/tool bodies as stubs
