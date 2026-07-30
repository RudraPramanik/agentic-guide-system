## ADDED Requirements

### Requirement: Hardened P4 Cursor prompt exists as step4.md
The project SHALL provide `docs/steps/step4.md` as the sole P4 implementation prompt, modeled on `docs/steps/step2.md` / `docs/steps/step3.md`.

The prompt MUST include:
- Prerequisites (P3 complete from `docs/context.md`)
- Prompt conventions and failure standards (`FAILURE BOUNDARY` + `✅ Failure path` per code step)
- P4 architecture / dependency graph and a single locked build order
- Locked design decisions (no optional/either-or language for P4 contracts)
- Sub-steps **4.0–4.8** with clear TASK bodies, plus **4.9** pytest and **4.10** smoke/real verification
- Full verification checklist and ship criteria table
- Citation that Planner SoT is `docs/blueprint_final.md` v6.1 (not a second conflicting blueprint)

#### Scenario: Agent can implement without inventing contracts
- **WHEN** an implementer opens `docs/steps/step4.md`
- **THEN** every P4 module has an ordered sub-step with explicit APIs, fallbacks, and a runnable ✅ validation command

#### Scenario: Blueprint remains SoT, prompt remains build contract
- **WHEN** product vocabulary or algorithms need authority
- **THEN** `docs/blueprint_final.md` v6.1 is cited as Planner SoT and `step4.md` encodes those locks for Cursor apply sessions

### Requirement: travel_engine is pure Python with injected routing
The travel engine under `src/travel_engine/` MUST contain no LLM calls and no network/DB I/O. Routing durations MUST be supplied only via an injected `RoutingProvider` protocol defined in `travel_engine/protocols.py`.

`RouteLeg` MUST carry `from_place_id`, `to_place_id`, `duration_min`, `distance_km`, and `used_fallback`.

No module under `src/travel_engine/` MUST import `src.geo`, `httpx`, SQLAlchemy session APIs, litellm, or Qdrant clients.

#### Scenario: Import graph stays clean
- **WHEN** static search is run for `src.geo` / `httpx` / litellm / qdrant under `src/travel_engine/`
- **THEN** there are zero matches

#### Scenario: Protocols import without geo
- **WHEN** `from src.travel_engine.protocols import RoutingProvider, RouteLeg` is executed
- **THEN** the import succeeds without loading geo gateways

### Requirement: Structural and interest vocabularies are split
`travel_rules.py` MUST keep structural constants keyed by `Place.category` (P2 locked set: `museum|viewpoint|monastery|attraction|park|trailhead`) separate from interest weights keyed by `Place.enriched_tags` membership (P3 `PLACE_TAG_VOCAB`).

`VISIT_DURATION_BY_CATEGORY` MUST include every P2 category. Duration lookup MUST use `.get(category, VISIT_DURATION_DEFAULT_MIN)` — never bare `[category]`.

`MORNING_ONLY_CATEGORIES` MUST NOT include `sunrise_point`. Interest-only keys (`trek`, `cultural`, …) MUST NOT appear as duration-map keys.

#### Scenario: Duration keys cover P2 categories
- **WHEN** `VISIT_DURATION_BY_CATEGORY` is inspected
- **THEN** its keys are a superset of `{museum, viewpoint, monastery, attraction, park, trailhead}`

#### Scenario: Unknown category uses default duration
- **WHEN** a place has `category="unknown_future"`
- **THEN** visit duration resolves to `VISIT_DURATION_DEFAULT_MIN` without raising `KeyError`

### Requirement: Place selection uses sum-of-weights scoring
`place_selector.select_places` MUST score each candidate as the **sum** of `CATEGORY_WEIGHTS[tag]` for tags present in both `place.enriched_tags` and `user_interests` (and present in `CATEGORY_WEIGHTS`).

Selection MUST apply `AVOID_SAME_DAY_PAIRS` conflict filtering on structural categories. Budget MUST be a soft preference only until a per-place cost field exists (no hard exclude invented in P4).

`explain_selection(...)` MUST return compact strings suitable for `tool_trace` / `rank_places` top explanations — NOT a new `TripEvaluation` column.

#### Scenario: Multi-interest outranks single interest
- **WHEN** one place matches two user interests and another matches one, with otherwise equal candidates
- **THEN** the multi-interest place ranks higher by sum score

#### Scenario: Empty enriched_tags scores zero and does not crash
- **WHEN** a candidate has `enriched_tags=[]`
- **THEN** its score is `0` and selection continues without raising

### Requirement: Day allocation respects caps and visit-time budget
`day_allocator.allocate_days` MUST distribute selected places into `days` lists, each with at most `MAX_PLACES_PER_DAY` places, visit durations via safe `.get(...)`, and visit-time within the locked active-day budget (8hr minus travel buffer semantics as stated in the prompt).

Geographic pre-clustering MUST seed same-day candidate pools for places within a 10km radius of each other (constant named in `travel_rules`).

#### Scenario: Eighteen places over three days stay within caps
- **WHEN** `allocate_days` is called with 18 scored places and `days=3`
- **THEN** it returns 3 lists, each with ≤6 places, and each day’s visit-time sum stays within the locked budget

### Requirement: Route optimization is permutation TSP with drop-retry
`route_optimizer.optimize_route` MUST:
- Call `routing.travel_matrix(...)` only (never import geo)
- Order stops by brute-force permutation search with fixed start at `base_lat`/`base_lng` (≤720 permutations at N=6)
- Add **no** TSP solver package
- If total travel exceeds `MAX_DAILY_TRAVEL_MIN`, drop the lowest-scored stop and retry (max 3 attempts)
- Surface `dropped_stops` as a list of `{place_id|name, reason}` records on the result

#### Scenario: Fake provider finds a lower-travel order
- **WHEN** unit tests inject a `FakeRoutingProvider` with asymmetric leg times
- **THEN** `optimize_route` returns the minimum-travel ordering without network I/O

#### Scenario: Over-budget day records drops
- **WHEN** every ordering exceeds `MAX_DAILY_TRAVEL_MIN`
- **THEN** the result includes one or more `dropped_stops` entries with reasons and still returns a best-effort ordered list

### Requirement: Schedule builder uses naive wall-clock times
`schedule_builder.build_day_schedule` MUST assign destination-local naive wall-clock `suggested_start_time` strings, apply visit durations via `.get(..., DEFAULT)`, force morning-only structural categories into early slots (order ≤ 2 / start ≤ locked morning cutoff), and insert the lunch break when the day spans `LUNCH_BREAK_START`.

Times MUST NOT be converted to UTC or attached to a timezone inside travel_engine.

#### Scenario: Six-stop day has valid morning placement
- **WHEN** a 6-stop ordered day includes a `viewpoint`
- **THEN** every stop has `suggested_start_time`, the first is ≥ `DAY_START_TIME`, and the viewpoint is in slot 1 or 2

### Requirement: Trip validator is a chain of named rule checks
`trip_validator.validate_trip` MUST return `ValidationResult(passed, warnings, errors)` and evaluate at least: daily travel cap, no repeated places across days, morning-only slot rules, at least one anchor attraction per day (score threshold locked in rules), and geographic coherence against a named std-dev threshold constant in `travel_rules`.

Each rule MUST be a separate check function (chain-of-responsibility style). The validator MAY observe PLAN-phase `dropped_stops` when shaping warnings/REPLAN hints, without implementing REPLAN tools.

#### Scenario: Good itinerary passes
- **WHEN** a fixture itinerary satisfies all rules
- **THEN** `errors` is empty and `passed` is true

#### Scenario: Injected violations produce specific errors
- **WHEN** the itinerary repeats a place or places a morning-only stop late
- **THEN** `errors` contains distinct, rule-specific messages (not a single opaque failure)

### Requirement: Planner routing adapter wraps geo outside travel_engine
`OsrmRoutingProvider` MUST live in `src/planner/routing_provider.py`, implement `RoutingProvider`, wrap `src/geo/osrm.py`, and map haversine/OSRM fallback onto `RouteLeg.used_fallback=True` (and any caller-visible fallback flag the prompt locks for P5 state).

P4 MUST also provide a minimal `ToolResult` + `execute_tool` skeleton: unknown tool → `ok=False`, never raise. Full registry and LangGraph remain P5.

#### Scenario: Unknown tool is a soft failure
- **WHEN** `execute_tool` is called with an unregistered name
- **THEN** it returns `ToolResult(ok=False, ...)` and does not raise

#### Scenario: Fallback legs are marked
- **WHEN** the underlying OSRM gateway returns `fallback_used=True`
- **THEN** corresponding `RouteLeg.used_fallback` values are true

### Requirement: CORS middleware is configured for credentialed explicit origins
The app MUST add `CORS_ALLOWED_ORIGINS: list[str]` via `get_settings()` and register FastAPI `CORSMiddleware` with `allow_credentials=True` and explicit origins only — never `["*"]` with credentials.

MVP cookie SameSite Option A (same registrable domain, keep `SameSite=Lax`) MUST be documented in `docs/context.md` as a deployment note without changing auth cookie code in P4.

#### Scenario: Configured origin receives CORS allow headers
- **WHEN** a browser preflight/request uses an origin listed in `CORS_ALLOWED_ORIGINS`
- **THEN** the response includes matching CORS allow headers

#### Scenario: Wildcard with credentials is forbidden
- **WHEN** settings are reviewed for CORS
- **THEN** credentials mode is not paired with origin `*`

### Requirement: P4 verification includes unit tests and real smoke proof
P4 MUST ship:
- Pytest coverage for rules, selector, allocator, optimizer (FakeRoutingProvider), schedule, validator, CORS, and import/purity guards
- A real verification path (script and/or checklist commands) proving end-to-end engine behavior on fixture data without requiring LangGraph
- `docs/context.md` updates only after validations pass

#### Scenario: Full pytest suite stays green
- **WHEN** `python -m pytest tests/ -v` runs after P4 implementation
- **THEN** prior tests plus new P4 tests pass

#### Scenario: Smoke proof does not need the planner graph
- **WHEN** the P4 smoke/real verification script runs with Fake or live OSRM as documented
- **THEN** it exercises select → allocate → optimize → schedule → validate and exits non-zero with a clear section header on failure (never ambiguous PASS)
