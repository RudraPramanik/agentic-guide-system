## Purpose

Planner blueprint source-of-truth rules: `docs/blueprint_final.md` v6.1 is the single master; competing addendum content must not live in `docs/blueprint.md`.

## Requirements

### Requirement: Single planner blueprint source of truth

`docs/blueprint_final.md` MUST be the authoritative Planner blueprint. After this change, `docs/blueprint.md` MUST NOT present competing LOCKED design content; it MUST point readers to `blueprint_final.md` (merged pre-flight) or contain only a short archival notice.

#### Scenario: Agent session uses one master doc
- **WHEN** an implementer needs Planner architecture, travel_engine rules, or P4–P6 step contracts
- **THEN** `docs/blueprint_final.md` MUST contain the current LOCKED definitions without requiring `docs/blueprint.md` for correctness

### Requirement: Corrected travel_rules vocabulary in master blueprint

The travel_rules design block in `docs/blueprint_final.md` MUST key structural constants (`VISIT_DURATION_BY_CATEGORY`, `MORNING_ONLY_CATEGORIES`) to P2 `Place.category` values including `attraction` and `trailhead`, MUST NOT include dead `sunrise_point`, MUST NOT use interest-only keys (`trek`, `cultural`) as duration map keys, MUST define `VISIT_DURATION_DEFAULT_MIN`, and MUST key `CATEGORY_WEIGHTS` to P3 interest tags. place_selector documentation MUST specify sum-of-matching-weights scoring and `.get(category, DEFAULT)` duration lookups.

#### Scenario: No sunrise_point in master rules
- **WHEN** the travel_rules section of `blueprint_final.md` is read
- **THEN** `MORNING_ONLY_CATEGORIES` MUST NOT list `sunrise_point` and MUST include `viewpoint` as the morning structural category

#### Scenario: Attraction duration present
- **WHEN** `VISIT_DURATION_BY_CATEGORY` is shown in the master blueprint
- **THEN** it MUST include an entry for `attraction` and for `trailhead`

### Requirement: Route optimizer algorithm and dropped_stops documented

The master blueprint MUST document brute-force permutation route ordering capped by `MAX_PLACES_PER_DAY` (no TSP package), and MUST require PLAN-phase drop-retry to surface `dropped_stops` with reasons for REPLAN coordination.

#### Scenario: Step 4.5 reflects locks
- **WHEN** P4 step 4.5 text in `blueprint_final.md` is read
- **THEN** it MUST mention permutation search (or equivalent exhaustive ordering) and `dropped_stops` output

### Requirement: P5 and P6 locks embedded in master blueprint

`docs/blueprint_final.md` MUST document: ToolContext (db/routing) outside LangGraph TravelState; preferred DB session-per-tool needing DB; SSE queue + background task with client disconnect cancel; `PLANNER_ABSOLUTE_MIN_PLACES` pre-graph floor; planner cache key including rounded `base_lat`/`base_lng`; guest ownership via `wandr_session` == `Trip.session_id`; explain_selection via tool_trace; agent no-tool nudge with one `tool_choice=required` retry then default tool.

#### Scenario: Cache key includes accommodation
- **WHEN** step 6.4 cache key description is read
- **THEN** it MUST include rounded base coordinates, not only destination_id + interests + days + budget

#### Scenario: SSE is producer-consumer
- **WHEN** step 6.2 streaming design is read
- **THEN** it MUST NOT specify only await-full-invoke-then-emit as the intended design; it MUST describe streaming events while the graph runs (queue or equivalent) and disconnect cancellation

### Requirement: CORS and SameSite decisions in master blueprint

The master blueprint MUST require `CORSMiddleware` with origins from settings and `allow_credentials=True` without wildcard origins, and MUST record MVP cookie SameSite Option A (same registrable domain / Lax).

#### Scenario: CORS documented before P6 frontend work
- **WHEN** environment or early-phase / P4 pre-flight sections are read
- **THEN** `CORS_ALLOWED_ORIGINS` (or equivalent settings name) MUST appear as a required configuration

### Requirement: Package install order reflects pytest at P1

The Package Install Order table in `docs/blueprint_final.md` MUST list `pytest` / `pytest-asyncio` / `pytest-mock` at the P1 test-harness step (1.11), not exclusively at a late 7.x step that contradicts shipped history.

#### Scenario: Pytest row location
- **WHEN** the Package Install Order table is read
- **THEN** pytest packages MUST be associated with step 1.11 (or equivalent P1 test step)
