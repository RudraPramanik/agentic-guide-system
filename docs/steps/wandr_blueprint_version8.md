# Wandr — Blueprint v8.3 (Amendment of v8.2: Deterministic-First, Eval-Gated, Agent-Executable)

> **Status:** v8.3 amends v8.2. v8.2 remains the target plan for Slices 0–8. v8.3 adds Slice 9 (post-save guidebook enrich: suggested stays and credited photos). Supersedes the v8 blueprint, the v8 addendum and v8.1.
> **Does not supersede** `docs/blueprint_final.md` (v6.1, shipped P0–P7) or `docs/v2_blueprint.md` (v7, shipped V0–V5). Those remain SSOT for what already exists.
> **Strategy:** Make the existing system correct, measurable and recoverable first. Add LLM reasoning only where the harness proves it helps.
> **Core rule:** *LLMs propose. Deterministic services verify and execute. The eval harness decides whether a change ships.*

---

## 0. How to read this document

| Part | Audience | Content |
|---|---|---|
| §1–§4 | Everyone | Decision, hierarchy, invariants, product targets |
| §5–§8 | Architects | Target architecture, contracts, flags, config, data |
| §9 | Coding agents | Slice and subslice execution table (the work) |
| §10 | Coding agents + CI | Machine-enforced guardrails |
| §11 | Everyone | Evaluation specification (the gate for everything) |
| §12–§16 | Ops/FE/Product | Reliability, FE contract, rollout, security, deferred work |
| §17–§19 | Coding agents | Operating protocol, stop conditions, report template |

Nothing in this file claims a module, endpoint or setting *already exists* unless it is named in `blueprint_final.md`, `v2_blueprint.md`, or `.env.example`. Everything else is **proposed** and must be verified in Slice 0 against the real checkout.

---

## 1. Executive decision

Wandr's biggest quality gains come from five things, in this order:

1. Understanding **where** the user wants to explore (location type, search area, trip base).
2. Retrieving **relevant, geographically appropriate** places.
3. Removing **duplicates and low-quality** candidates.
4. Building **realistic, internally consistent** day schedules and routes.
5. **Catching bad itineraries before publishing** and measuring quality continuously.

Multi-agent orchestration is **not** on that list. It is an optional, flag-gated experiment (Slice 7) that must beat the current planner on the golden set within latency and cost targets, or it does not ship.

### What you get if this is implemented faithfully

| Outcome | Source slice |
|---|---|
| Landmark vs city vs pin searches behave differently and predictably; no hidden 30 km radius | S3 |
| No duplicate stops, no impossible schedules, stronger validator with structured findings | S4 |
| Destinations judged "ready" on distribution and diversity, not just a count of 10 | S5 |
| Guide-agent points, markers, route and cards share one canonical ID set | S6 |
| No duplicate trips on retry; run status; reconnect | S1 |
| Regression gate that blocks quality loss, reproducible in CI | S2 |
| Evidence on whether agents/judge are worth their cost | S7 |
| Suggested stays near the trip base, with unknown price and availability, that are not route stops | S9 |
| Each stop shows a credited free photo, or the existing non-photo fallback when none exists | S9 |

---

## 2. Source-of-truth hierarchy

| Source | Authority |
|---|---|
| `AGENT.md` | Hard coding guardrails (extended by §10) |
| `docs/context.md` | Actual implementation status (verified facts only) |
| Existing source code + tests | Runtime truth and authoritative interfaces |
| `docs/blueprint_final.md` | v6.1 P0–P7 decisions |
| `docs/v2_blueprint.md` | v7 retrieval + observability decisions |
| `docs/FE_guide.md` | Frontend HTTP/SSE contract |
| **This document** | v8.3 target architecture and sequence (v8.2 plus Slice 9) |

**Conflict rule (hard):** if this document conflicts with code or a locked contract, the coding agent **halts that subslice**, writes an ADR proposal describing the conflict, and waits for approval. It does not pick a side and continue.

---

## 3. Non-negotiable invariants

### 3.1 Inherited (v6.1 + v7, unchanged)

- Router → Service → Repository. Routers never touch the DB.
- LLM calls only via `src/core/llm/client.py` (LiteLLM). No provider SDK imports elsewhere.
- Geo calls only via `src/geo/`. `travel_engine/` has no LLM, network or DB I/O; routing is injected via `RoutingProvider`.
- All env access through `get_settings()`. No hardcoded URLs/constants outside `config.py` / `travel_rules.py`.
- Every external call: explicit timeouts, tenacity retry per the Resilience Contracts table, named fallback, never a 500.
- Planner: `AgentPhase`, `PHASE_TOOLS`, `TOOL_REGISTRY`, `execute_tool()`, `apply_tool_result` as sole state writer, `tool_executor_node` as sole `execute_tool` caller, `ToolContext` only via `config["configurable"]["tool_context"]`, validate-before-`finish_plan`.
- No `AsyncSession` or `RoutingProvider` in serialized graph state. No closure/global request context on the cached compiled graph.
- Every generation and every edit is recorded in `evaluation/`.
- `ApiResponse[T]` / `PaginatedResponse[T]` for every endpoint. Existing HTTP paths, DTO shapes and SSE event names are byte-compatible unless an ADR approves otherwise.
- Existing `travel_engine/protocols.py::RouteLeg` (minutes/km) is **not redefined**. New consumers adapt to it.

### 3.2 New in v8.2

| # | Invariant |
|---|---|
| N1 | **Harness before behavior change.** No ranking, location, engine or planner behavior change merges before the S2 harness gate exists and baseline is frozen. |
| N2 | **Every behavior-changing slice has a kill-switch flag** that restores the old path, plus old-vs-new comparison on the golden set. |
| N3 | **Deterministic critical findings are never overridden** by a judge, a score, or an agent. |
| N4 | **No LLM output is authoritative for** IDs, coordinates, geometry, order, times, prices, availability, opening hours. |
| N5 | **One canonical trip** (stop IDs, day IDs, order, geometry) drives cards, guide points, markers, GeoJSON, edits, persistence and evaluation. |
| N6 | **Unknown stays unknown.** Missing opening hours, price, availability, timezone are represented as unknown, never defaulted to "open/free/available". |
| N7 | **Every accepted run reaches a terminal status.** |
| N8 | **Evals are reproducible in CI** via recorded LLM fixtures; live-model runs are a separate scheduled job. |
| N9 | **An uncalibrated LLM judge never gates or triggers repairs in the request path.** |
| N10 | **No silent provider/model switching.** The actual provider, model and fallback reason are recorded per execution. |

### 3.3 New in v8.3

| # | Invariant |
|---|---|
| N11 | **Media and lodging HTTP never run inside** `POST /planner/generate`. |
| N12 | **A stay suggestion is not a stop.** It does not enter the route unless the user adds it through the existing add-stop path. |
| N13 | **Slice 9 price and availability stay `unknown`.** Nothing in Slice 9 verifies them. |
| N14 | **A photo with no attribution is not shown.** |
| N15 | **A stop with no photo keeps the non-photo fallback.** Stock is not a photo of that place. |

---

## 4. Product targets (numbers that gate releases)

Slice 0 measures the baseline. Targets below are expressed relative to baseline where an absolute number would be a guess. **Any number marked `[SET IN S0]` must be filled from the measured baseline before S3 starts.**

| Target | Value | Gate |
|---|---|---|
| Generate p95 latency | ≤ 45 s (existing `PLANNER_GENERATION_TIMEOUT_SECONDS`) | Hard; never raised to make a feature fit |
| Generate p50 latency | ≤ baseline × 1.10 `[SET IN S0]` | Release gate |
| LLM calls per trip | ≤ baseline + 2 `[SET IN S0]` | Release gate for S7 |
| Tokens per trip | ≤ baseline × 1.25 `[SET IN S0]` | Release gate for S7 |
| Cost per trip | ≤ baseline × 1.25 `[SET IN S0]` | Release gate for S7 |
| Published trips with critical finding | 0 | Hard |
| Duplicate stops in published trips | 0 | Hard |
| Duplicate trips from retry/reconnect | 0 | Hard |
| Golden-suite pass rate (deterministic assertions) | 100% of non-quarantined cases | Hard |

If a feature cannot meet latency, the answer is **a background job with progress + run status**, not a longer SSE ceiling. That decision is made with product, with measured data, via ADR.

---

## 5. Target architecture

### 5.1 Request flow (target)

```text
Frontend
  │  destination query / selected point / radius / prefs
  ▼
Planner router (SSE, unchanged contract; additive fields)
  ▼
Planner service ── run_id + idempotency + tracing + budget
  ▼
Existing planner graph (phase-gated tool loop)  ◄── always the fallback path
  │
  ├─ [S3, flag] Location resolution (deterministic service)
  │     └─ LocationResolution → DiscoveryAnchor, SearchArea, TripBase
  ├─ Retrieval (existing Qdrant hybrid + PostGIS fallback), constrained to SearchArea
  ├─ [S4, flag] Candidate normalization + dedup + evidence-aware scoring
  ├─ [S7, flag, optional] Experience reasoner (LLM; priorities only)
  ├─ Deterministic engine: cluster → allocate → optimize → schedule
  ├─ Deterministic validator V2 (structured findings; critical blocks publish)
  ├─ [S7, flag, optional, sampled] Qualitative critic (advisory only)
  ├─ Narrative (existing write_narrative; cannot change structure)
  ▼
Canonical trip persistence (idempotent) + evaluation record
  │
  ├─▶ SSE / Trip API / GeoJSON / existing map + guide agent
  │     (generate ends here; still ≤ 45 s)
  │
  └─▶ after the trip exists, outside the planner graph and outside generate
        ├─ [S9, LODGING_V1_ENABLED] lodging search inside SearchArea → suggested stays
        └─ [S9, MEDIA_ENRICH_ENABLED] media resolve per stop → credited photo or empty list
```

### 5.2 What is a service vs an agent

| Capability | Kind | Why |
|---|---|---|
| Location resolution, search-area building | Deterministic service | Facts from providers, not reasoning |
| Retrieval, dedup, clustering, allocation, routing, scheduling, validation | Deterministic service | Must be reproducible and testable |
| Persistence, run tracking | Deterministic service | Integrity |
| Interpreting qualitative preferences | LLM role (optional) | Language reasoning |
| Qualitative itinerary critique | LLM role (optional, advisory) | Semantic judgment |
| Narrative | LLM (existing) | Language |
| Lodging retrieval and stay suggestions (S9) | Deterministic service | Mapped places inside the search area; no booking facts |
| Place media resolution (S9) | Deterministic service | Provider lookup after save; attribution or nothing |

At most **two** new LLM roles ever (reasoner, critic). Slice 9 adds none. Everything else stays code.

### 5.3 Module layout (additive; reuse existing modules wherever they satisfy the contract)

```text
src/
  location_intelligence/         # NEW (S3)
    schemas.py  resolver.py  search_area.py  confidence.py  service.py
  planner/
    runs/                        # NEW (S1) run tracking, idempotency
      models.py repository.py service.py
    reasoning/                   # NEW (S7, flag-gated) reasoner/critic role wrappers
  travel_engine/                 # EXTENDED (S4) — still pure Python
    candidate_normalizer.py      # NEW
    findings.py                  # NEW  ValidationFinding, Severity
    (existing: place_selector, day_allocator, route_optimizer,
     schedule_builder, trip_validator, protocols, travel_rules)
  evaluation/                    # EXTENDED (S2)
    scorers.py (existing)  metrics/  fixtures/  judge/ (offline)
  geo/
    media/                       # NEW (S9) photo facade only; lodging stays on geo + places
evals/
  golden/  baselines/  runs/  replay/   # replay/ = recorded LLM fixtures (N8)
tests/
  architecture/                  # NEW (§10) import + contract rules
  snapshots/                     # NEW (S0) frozen API/SSE/GeoJSON
```

Do not move existing modules. Do not create a second LLM client, second search implementation or second trip model.

---

## 6. Contracts

> Conceptual contracts. **Inspect existing schemas first and adapt; never create duplicate types.** Names below are proposals.

### 6.1 Location

```python
class LocationType(str, Enum):
    COUNTRY="country"; REGION="region"; CITY="city"; NEIGHBORHOOD="neighborhood"
    LANDMARK="landmark"; POI="poi"; ADDRESS="address"; MAP_PIN="map_pin"

class ResolvedLocation(BaseModel):
    canonical_name: str
    location_type: LocationType
    lat: float; lng: float                      # validated ranges
    country_code: str | None
    admin_area: str | None
    provider: str; provider_id: str | None      # e.g. nominatim osm_place_id
    confidence: float                           # 0..1
    bounding_box: list[float] | None
    boundary_geojson: dict | None               # validated geometry only

class LocationResolution(BaseModel):
    status: Literal["resolved","ambiguous","not_found"]
    selected: ResolvedLocation | None
    candidates: list[ResolvedLocation]          # populated when ambiguous
    requires_confirmation: bool
    reason: str | None
```

### 6.2 Three separate geographic concepts (never interchangeable)

| Concept | Meaning | Used by |
|---|---|---|
| **Discovery anchor** | What the user searched/selected | UI display, search-area construction |
| **Search area** | Boundary/radius from which candidates may be retrieved | Retrieval filter, validator `OUT_OF_SEARCH_AREA` |
| **Trip base** | Route start/end (hotel, address, chosen point) | Route optimizer, schedule |

```python
class SearchArea(BaseModel):
    strategy: Literal["city_boundary","admin_boundary","radius","polygon"]
    anchor: ResolvedLocation
    radius_km: float | None
    boundary_geojson: dict | None
    fallback_used: bool                         # N6: disclose, never hide
    description: str
```

**Legacy mapping:** existing `destination_id` + `base_lat/base_lng` map to (anchor = destination center, search area = current behavior, trip base = `base_lat/base_lng`). With `LOCATION_V2_ENABLED=false` the legacy path runs unchanged.

### 6.3 Search-area policy

| Input type | Behavior | Fallback (disclosed) |
|---|---|---|
| City | City/admin boundary | `LOCATION_CITY_FALLBACK_RADIUS_KM` around center |
| Neighborhood | Boundary or small radius | `LOCATION_NEIGHBORHOOD_RADIUS_KM` |
| Landmark / POI | Point radius `LOCATION_POI_RADIUS_KM` | — |
| Address | Small local radius | — |
| Map pin | User point + user radius (≤ `LOCATION_MAX_RADIUS_KM`) | — |
| Polygon | Supplied polygon (validated) | — |
| Ambiguous | `requires_confirmation=True`; never auto-picks below threshold | — |
| Not found | `not_found`; never substitutes a city center | — |

Auto-resolve only if `confidence ≥ LOCATION_AUTO_RESOLVE_CONFIDENCE` **and** exactly one candidate clears it.

### 6.4 Candidate and validation contracts

```python
class PlaceCandidate(BaseModel):
    place_id: UUID                              # canonical; reject if missing
    name: str; lat: float; lng: float
    category: str | None
    enriched_tags: list[str] = []
    source: str; source_id: str | None
    evidence: list[EvidenceRef] = []
    opening_hours_raw: str | None               # original OSM string, preserved
    opening_hours_status: Literal["verified","unknown","malformed"] = "unknown"

class Severity(str, Enum):
    CRITICAL="critical"; ERROR="error"; WARNING="warning"; INFO="info"

class ValidationFinding(BaseModel):
    code: str                                   # stable, see §6.5
    severity: Severity
    day: int | None
    stop_ids: list[UUID] = []
    message: str
    repairable: bool
    suggested_action: str | None                # a deterministic action name
    blocks_publish: bool
```

### 6.5 Finding codes (stable; never renamed, only added)

`DUPLICATE_STOP`, `INVALID_COORDINATES`, `MISSING_PLACE_ID`, `OUT_OF_SEARCH_AREA`, `EXCESSIVE_TRAVEL_TIME`, `OVERLOADED_DAY`, `OPENING_HOURS_CONFLICT` (verified only), `OPENING_HOURS_UNKNOWN` (info), `MISSING_ROUTE_GEOMETRY`, `ROUTE_SCHEDULE_MISMATCH`, `NON_CHRONOLOGICAL_SCHEDULE`, `UNREALISTIC_VISIT_SEQUENCE`, `INSUFFICIENT_EVIDENCE`, `MORNING_ONLY_VIOLATION`, `NO_ANCHOR_ATTRACTION`, `GEO_INCOHERENT_DAY`.

Critical (blocks publish): `DUPLICATE_STOP`(high identity confidence), `INVALID_COORDINATES`, `MISSING_PLACE_ID`, `OUT_OF_SEARCH_AREA`, `MISSING_ROUTE_GEOMETRY` (only when mode promises geometry), `ROUTE_SCHEDULE_MISMATCH`, `NON_CHRONOLOGICAL_SCHEDULE`, `OPENING_HOURS_CONFLICT`.

### 6.6 Canonical trip (reuse existing `Trip`/`TripPlace`; add only what S6 proves missing)

Invariants: stable stop IDs; stable day numbering; `order_in_day` authoritative; route geometry corresponds to that order; suggested-vs-confirmed is a **status field on the same ID space**, not a parallel list; geometry provenance is recorded (`osrm` / `haversine_estimate` / `none`) and the UI never presents estimates as road geometry.

### 6.7 Run tracking (S1)

```python
class RunStatus(str, Enum):
    ACCEPTED="accepted"; RESOLVING="resolving"; RESEARCHING="researching"
    PLANNING="planning"; VALIDATING="validating"; COMPLETED="completed"
    PARTIAL="partial"; DEGRADED="degraded"; FAILED="failed"
    CANCELLED="cancelled"; TIMED_OUT="timed_out"
```

Terminal: `COMPLETED, PARTIAL, DEGRADED, FAILED, CANCELLED, TIMED_OUT`. Transitions are code-owned; an LLM can never change status.

### 6.8 Guidebook enrich (S9, proposed — verify in S0; do not treat as present)

```python
class LodgingSuggestion(BaseModel):
    place_id: UUID
    name: str
    lat: float
    lng: float
    category: Literal["lodging"]
    distance_to_base_km: float
    price_status: Literal["unknown"] = "unknown"
    availability_status: Literal["unknown"] = "unknown"
    # no price, booking URL, or rating

class PlaceMedia(BaseModel):
    url: str
    source: Literal["osm", "wikimedia", "opentripmap"]
    attribution: str          # required; missing attribution ⇒ do not show
    fetched_at: datetime
```

A `LodgingSuggestion` is a place already stored with `category=lodging`. It is not a second place model and not a stop.

---

## 7. Feature flags and configuration

All via `src/config.py` / `get_settings()`. **Audit existing `Settings` and `.env.example` first; reuse names where equivalents exist.** Defaults preserve current behavior.

### 7.1 Flag matrix

| Flag | Default | Slice | Off ⇒ |
|---|---|---|---|
| `RUN_TRACKING_ENABLED` | `false` → `true` after S1 soak | S1 | No run rows; current behavior |
| `LOCATION_V2_ENABLED` | `false` | S3 | Legacy destination/base behavior |
| `TRAVEL_ENGINE_V2_ENABLED` | `false` | S4 | Existing selector/allocator/scheduler |
| `VALIDATOR_V2_ENFORCE` | `false` | S4 | V2 findings computed + logged, not blocking (shadow) |
| `READINESS_V2_ENABLED` | `false` | S5 | Existing `compute_readiness` |
| `CANONICAL_TRIP_V2_ENABLED` | `false` | S6 | Existing trip/map payloads |
| `REASONING_LAYER_ENABLED` | `false` | S7 | Existing planner only |
| `REASONING_SHADOW_SAMPLE_RATE` | `0.0` | S7 | No shadow runs (cost cap) |
| `EVALUATION_JUDGE_ENABLED` | `false` | S2/S7 | No judge calls |
| `LODGING_V1_ENABLED` | `false` | S9 | Stay block keeps today's static copy |
| `MEDIA_ENRICH_ENABLED` | `false` | S9 | No media HTTP and no media reads on the request path |

**Valid combinations:** shadow runs require `REASONING_LAYER_ENABLED=false` and `REASONING_SHADOW_SAMPLE_RATE>0`; a shadow run **never** persists a trip, never alters the response, and is budget-capped. `REASONING_LAYER_ENABLED=true` is only legal after the S7 gate passes (§11.9).

### 7.2 Proposed settings (verify names; add only what is used)

```env
# Location (S3)
LOCATION_AUTO_RESOLVE_CONFIDENCE=0.90
LOCATION_POI_RADIUS_KM=10
LOCATION_NEIGHBORHOOD_RADIUS_KM=5
LOCATION_CITY_FALLBACK_RADIUS_KM=15
LOCATION_MAX_RADIUS_KM=50

# Readiness V2 (S5)
READINESS_MIN_USABLE_PLACES_PER_DAY=4
READINESS_MIN_CATEGORIES=3
READINESS_MIN_CLUSTERS_MULTI_DAY=2

# Reasoning (S7, optional)
ORCHESTRATION_MAX_AGENT_INVOCATIONS=2
ORCHESTRATION_MAX_REPAIR_ATTEMPTS=0
AGENT_REASONING_MODEL=          # empty ⇒ LLM_MODEL
AGENT_CRITIC_MODEL=             # empty ⇒ LLM_MODEL

# Eval (S2)
EVALUATION_JUDGE_TIMEOUT_SECONDS=15

# Guidebook enrich (S9) — proposed; add only when that subslice uses them
# MEDIA_SOURCES=osm,wikimedia,opentripmap
# WIKIMEDIA_USER_AGENT=
```

Existing values (`LLM_*`, `PLANNER_*`, `ROUTING_BACKEND`, `SEARCH_*`, `QDRANT_*`, CORS, etc.) are **not** overwritten. No new mandatory API key. Reuse an existing OpenTripMap key if that source is already configured. Never raise `PLANNER_GENERATION_TIMEOUT_SECONDS` to fit a feature. Slice 9 does not add a lodging-count or photo-coverage gate to §4.

---

## 8. Data, readiness, opening hours, dates, cost

### 8.1 Database changes (additive Alembic only)

Add only what a slice proves necessary:

| Table / column | Slice | Purpose |
|---|---|---|
| `planner_runs` (run_id, session_id, user_id?, idempotency_key, status, input_hash, trip_id?, failure_code, timestamps, workflow_version, model/provider/fallback info) | S1 | Run status + idempotency |
| Unique `(session_id|user_id, idempotency_key)` | S1 | Duplicate-trip prevention |
| `trips.search_area` (JSONB), `trips.discovery_anchor` (JSONB) | S3 | Traceability of area/anchor |
| Stop status (`confirmed`/`suggested`) on existing stop entity | S6 | Guide-agent unification |
| `trips.version` (int) | S6, only if audit shows no versioning | Optimistic concurrency (explicit task) |
| Feedback table | S2/S6, only if not present | User signals |
| `places.media` (JSONB list of `PlaceMedia`) | S9 | Cached credited photos; additive column only |
| Lodging rows on existing `places` (`category=lodging`) | S9 | Suggested stays; no lodging table |

Every migration: forward + rollback tested on empty DB and a production-like snapshot; no destructive change; compatible with the previous app version (expand/contract).

### 8.2 Readiness V2 (replaces "≥10 places")

`PLANNER_ABSOLUTE_MIN_PLACES=10` remains a **pre-graph floor** (no LLM spend). Readiness V2 adds, for the requested `days`:

| Check | Rule (configurable) |
|---|---|
| Usable places | ≥ `days × READINESS_MIN_USABLE_PLACES_PER_DAY` after dedup + coordinate validation |
| Category diversity | ≥ `READINESS_MIN_CATEGORIES` distinct categories |
| Geographic spread | For `days>1`: ≥ `READINESS_MIN_CLUSTERS_MULTI_DAY` clusters (10 km pre-cluster), no single cluster > 70% of places |
| Coordinate validity | 100% of counted places |
| Evidence quality | Share of places with source + retrieval timestamp |

Output remains `ready | limited | sparse` with a human-readable `message`; low readiness warns (as today), it does not block above the floor. Add an ingestion report per destination (counts, category distribution, dup rate, ingestion failures, freshness).

### 8.3 Opening hours

- Source: OSM `opening_hours` already in raw tags. Preserve the original string.
- Parse only with a vetted parser (new package = `requirements.txt` + why-comment, ADR if non-trivial). Unparseable ⇒ `malformed`; absent ⇒ `unknown`.
- Only `verified` hours can raise `OPENING_HOURS_CONFLICT`. `unknown` ⇒ `OPENING_HOURS_UNKNOWN` (info). Never block on unknown unless the user explicitly requires confirmed hours.
- Until this lands, no document, UI or agent may claim "open now".

### 8.4 Dates and timezone (honest scope)

The engine uses **naive destination-local wall-clock** (v6.1 lock). **Decision for v8.2: defer** date-specific, seasonal and daylight logic. `start_date` may be accepted and stored but must not drive scheduling until a timezone ADR (IANA tz per destination, tz-aware engine, migration of serialized times) is approved. No feature may claim seasonal/sunrise awareness before then.

### 8.5 Cost semantics

Place/activity cost uses labels: `free`, `estimated`, `source_verified`, `unknown`. Never invent prices. LLM token/cost tracking is separate from trip expense data. Slice 9 lodging uses `unknown` for both price and availability.

---

## 9. Implementation plan — slices and subslices

> Each subslice = one PR. Each lists **allowed paths**, **required tests**, a **verify command**, a **rollback**, and **stop conditions**. Anything outside "allowed paths" is forbidden for that subslice. Path names assume the v6.1 layout; confirm in S0.

**Order (locked):**

```
S0 Audit + baseline + guardrails + frozen snapshots
S1 Run tracking + idempotency            (before behavior change → clean attribution)
S2 Eval harness hardening                 (gate for everything below)
S3 Location intelligence
S4 Travel engine V2 + validator V2
S5 Readiness V2 + opening hours + ingestion quality
S6 Canonical trip / map / guide unification
S7 Experimental reasoning (optional, evidence-gated)  ─┐ after S6; S7 may stay off
S9 Guidebook enrich (stays + credited photos)         ─┘ after S6.2; not gated on S7
S8 Rollout + hardening
```

S9 runs after Slice 6 and may run beside Slice 7. It does not wait for the Slice 7 ship gate. Entry requires 6.2 (canonical `place_id`, suggested versus routed).

### Slice 0 — Audit, baseline, guardrails

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 0.1 | Repository truth audit → `docs/v8.2/repository_audit.md`: status matrix (implemented-tested / implemented-untested / partial / stub / deferred) with file/symbol/test links; settings inventory; FE map/guide integration map; SSE lifecycle. Also record today's display-only `accommodation_label`, gradient stop cards, and the trip-page copy "Stays are unavailable" so Slice 9 does not treat them as real lodging or photos | `docs/v8.2/**` only | n/a | Every row links to a path/symbol/test | delete docs | Blueprint claim contradicts code (record, continue audit) |
| 0.2 | Frozen snapshots: request/response fixtures for destination search, readiness, planner SSE event sequence, trip CRUD, GeoJSON, day edits, guest vs authed | `tests/snapshots/**`, `tests/fixtures/**` | Snapshot tests green on clean checkout, no live network | `pytest tests/snapshots -v` | delete tests | Existing suite already red (halt, report) |
| 0.3 | Baseline metrics → `docs/v8.2/baseline_metrics.md` + `evals/baselines/`: pass rate, invalid-trip rate, duplicate rate, coherence, schedule feasibility, p50/p95 latency, LLM calls/tokens/cost per trip, OSRM/geo fallback rates, persistence failures | `docs/v8.2/**`, `evals/baselines/**`, `scripts/` (read-only use) | Baseline reproducible twice within tolerance | `python scripts/run_evals.py` ×2 | delete files | Baseline not reproducible (fix nondeterminism first) |
| 0.4 | Fill every `[SET IN S0]` in §4 from baseline; record ADR-001…ADR-004 (modular monolith, API v1 compat, bounded execution, deterministic-vs-judge) | `docs/v8.2/**` | n/a | Targets table has no placeholders | revert docs | Latency baseline already > 45s p95 (halt; product decision) |
| 0.5 | Architecture tests (§10): import rules, no-`os.environ`, no litellm outside gateway, no I/O imports in `travel_engine` | `tests/architecture/**`, CI workflow | Tests pass on current code (or violations listed and ticketed) | `pytest tests/architecture -v` | remove tests | Existing violations found (report; do not "fix" unrelated code) |

**Exit gate:** existing suite + snapshots + baseline + architecture tests green; no production behavior changed.

### Slice 1 — Run tracking and idempotency

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 1.1 | `planner_runs` migration + model + repo (additive) | `alembic/versions/`, `src/planner/runs/**` | Migration up/down on empty + snapshot DB; unique-constraint test | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` | `RUN_TRACKING_ENABLED=false`; downgrade | Needs destructive change |
| 1.2 | Run lifecycle service: create run, code-owned status transitions, terminal statuses, structured failure codes | `src/planner/runs/**`, `src/planner/service.py` | Transition table tests incl. illegal transitions; every path ends terminal (timeout, abort, disconnect, LLM down) | `pytest tests/planner/runs -v` | flag off | Planner service contract would change SSE |
| 1.3 | Idempotency: key from client header (fallback: hash of normalized request + session) ; same key ⇒ same run/trip; unique-persist guard in `TripService.save_from_state` | `src/trips/service.py`, `src/planner/service.py`, `src/planner/runs/**` | Double-submit ⇒ one trip; crash-after-save-before-SSE ⇒ retrievable by run_id; concurrent duplicates | `pytest tests/trips tests/planner -k idempotent` | flag off | Cache-key semantics conflict (6.4 cache is parsed-pref level) — ADR |
| 1.4 | Additive endpoints `GET /api/v1/planner/runs/{run_id}` (+ cancel if practical); ownership rules same as trips (guest cookie must match) | `src/planner/router.py`, `src/planner/schemas.py`, `docs/FE_guide.md` | Ownership 403; envelope; snapshot of legacy endpoints unchanged | `pytest tests/snapshots tests/planner -v` | remove routes | Would change existing SSE event names |

Cancellation: client disconnect already cancels the background task (v6.1 §6.2); 1.4 adds explicit cancel only if it fits cleanly. Defer leases, checkpoint/resume, workers.

**Exit gate:** legacy snapshots green; duplicate-trip rate 0 in tests; every run terminal.

### Slice 2 — Evaluation harness hardening (the gate)

Full spec in **§11**. Subslices:

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 2.1 | Golden schema v2 + loader validation (case types, expected assertions, labels, quarantine flag) | `evals/**`, `src/evaluation/**` | Bad case fails fast with named error | `pytest tests/evaluation -v` | revert | Existing cases would break (migrate, don't delete) |
| 2.2 | LLM record/replay layer (fixtures in `evals/replay/`) — implemented at the gateway seam only | `src/core/llm/client.py` (replay hook behind setting), `evals/replay/**` | Replay yields identical output twice; missing fixture ⇒ clear failure | `python scripts/run_evals.py --replay` ×2 identical | setting off | Needs provider SDK import outside gateway |
| 2.3 | Metrics module: location, retrieval (recall@k), duplicates, coherence, feasibility, preference, persistence, map/itinerary consistency | `src/evaluation/metrics/**`, `src/evaluation/scorers.py` | Pure-function unit tests with hand-computed expectations | `pytest tests/evaluation -v` | revert | — |
| 2.4 | Property/metamorphic tests for the engine (§11.6) | `tests/travel_engine/**` | See §11.6 | `pytest tests/travel_engine -v` | revert | A property fails on current engine (report as finding; do not alter engine here) |
| 2.5 | Gate runner: baseline diff with tolerance bands, `--update-baseline` explicit, non-zero exit on regression; CI job (replay mode on PR; live mode nightly) | `scripts/run_evals.py`, `.github/workflows/**` | Seeded regression ⇒ named non-zero diff | CI green on main | remove job | — |
| 2.6 | Offline judge scaffold (LiteLLM via gateway; prompt/rubric versioned; sampled; never in request path) + human-review sheet format | `src/evaluation/judge/**`, `evals/human_review/**` | Judge output schema validation; judge failure ⇒ deterministic eval unaffected | `pytest tests/evaluation -k judge` | `EVALUATION_JUDGE_ENABLED=false` | Judge needs a new provider SDK |

**Exit gate:** reproducible replay run; regression is detected on a seeded bad change; golden minimums (§11.2) met.

Gate correction recorded while closing 2.5: generate is always for a destination id that is already chosen, so the agent prompt names that destination and a clarification that asks which destination does not end the run. A discover loop that repeats without places forces one `search_places` before it may abort. A plan loop that repeats without a schedule forces one `build_schedule` before it may abort. Day allocation does not place a cluster farther than the 10 km pre-cluster onto a day that already holds another region; those places are omitted so a published day can pass the existing geo-coherence check. Slice 4.3 may tune the same rule. It does not put distant places back onto a near day. Catalog words in the traveler's text are interests even when the parser names a place instead (`photography` stays photography; `sunrise` and `sunset` are viewpoint). When the trip has a stop above the anchor score, a day whose stops all fall at or below that score is left empty and is not published. When no stop clears that score, because the traveler named no catalog interest, a place whose catalog tag weight is above the same score anchors the day. `finish_plan` records the engine validation of the itinerary it publishes.

### Slice 3 — Location intelligence (`LOCATION_V2_ENABLED`)

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 3.1 | Candidate search: reuse `geo/geocoder` + destination catalog; return multiple normalized candidates with type, parent, provider ids, confidence, explanation | `src/location_intelligence/**`, `src/geo/schemas.py` (additive) | Fixtures: "Darjeeling"=city, "Tiger Hill"=landmark, "Ghoom Monastery"=POI; same fixture ⇒ same output | `pytest tests/location_intelligence -v` | flag off | Needs a new geocoding provider (ADR) |
| 3.2 | Classification + resolution + ambiguity/confidence per §6.3; geocoder `None` ⇒ `not_found` (never default city) | same | Ambiguous names ⇒ multiple candidates; low confidence ⇒ confirmation required | same | flag off | — |
| 3.3 | Search-area builder per §6.3, validated geometry, server-side max radius, disclosed fallback | `src/location_intelligence/search_area.py` | City ≠ landmark behavior; polygon validation; radius clamp; fallback flagged | same | flag off | — |
| 3.4 | Planner integration: legacy request mapped to internal model; retrieval constrained to `SearchArea` (PostGIS fallback uses same area); `discovery_anchor`/`search_area` stored on trip | `src/planner/**`, `src/destinations/service.py`, `src/search/places_index.py` (filter only), `src/trips/**` (additive column) | Legacy snapshot unchanged with flag off; golden location cases | `pytest tests/snapshots tests/planner -v && python scripts/run_evals.py --replay --suite location` | flag off | Would redefine `base_lat/base_lng` semantics (ADR) |
| 3.5 | Additive endpoints `locations/search`, `locations/resolve`, `locations/search-area` (only if S0 confirms gap and FE agrees) | `src/location_intelligence/router.py`, `docs/FE_guide.md` | Envelope, auth, rate-limit | `pytest tests/location_intelligence -v` | remove router | FE contract not agreed |
| 3.6 | FE contract + stub fixtures: candidate list with type labels, selected point, radius control, search-area preview, anchor vs base distinction | `docs/FE_guide.md`, `docs/blueprint_frontend.md`, FE repo (owner-assigned) | FE contract tests against backend fixtures | FE CI | revert FE | No FE owner assigned (halt S3 release; backend may ship dark) |

**Exit gate:** location golden cases pass thresholds (§11.4); legacy clients unchanged; no hidden 30 km in the V2 path (grep + test).

### Slice 4 — Travel engine V2 and validator V2 (`TRAVEL_ENGINE_V2_ENABLED`, `VALIDATOR_V2_ENFORCE`)

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 4.1 | Candidate normalizer: name/category/coordinate normalization, exact-ID + normalized-name + proximity + alias + parent/child dedup; confidence-based; user-selected places retained; **no aggressive merging** | `src/travel_engine/candidate_normalizer.py` | Same monastery variants collapse; adjacent distinct attractions stay | `pytest tests/travel_engine -k normalizer` | flag off | — |
| 4.2 | Evidence-aware scoring: keep v6.1 sum-of-matching-weights as base; add configured terms (diversity, geo fit, evidence, dup penalty); weights in `travel_rules.py`; explanations into `tool_trace` (no schema change) | `src/travel_engine/place_selector.py`, `travel_rules.py` | Old behavior byte-identical with flag off; golden preference cases | `pytest tests/travel_engine && run_evals --replay` | flag off | Weight change not backed by golden evidence |
| 4.3 | Clustering/allocation: tune existing 10 km pre-cluster, `MAX_PLACES_PER_DAY`, 8 h budget; **compare against current implementation first** (report); no new clustering lib without ADR | `src/travel_engine/day_allocator.py` | Coherence metric ≥ baseline; each day ≤ limits | same | flag off | New dependency proposed |
| 4.4 | Route optimizer: keep permutation search + `dropped_stops` + 3-attempt cap; add base→first / last→base legs when trip base set; adapt to existing `RouteLeg` | `src/travel_engine/route_optimizer.py` | `FakeRoutingProvider` unit tests; routing-failure ⇒ haversine fallback preserved | same | flag off | `RouteLeg` change required (ADR) |
| 4.5 | Schedule builder: real leg durations (no fixed spacing), meals, buffers, morning-only, verified hours only; naive wall-clock retained | `src/travel_engine/schedule_builder.py` | Chronological; fits day; morning-only in slots ≤2; unknown hours not treated as open | same | flag off | Needs tz support (deferred — ADR) |
| 4.6 | Validator V2: all §6.5 findings, severity, blocks_publish, repairable + deterministic `suggested_action`; shadow first (`VALIDATOR_V2_ENFORCE=false`), enforce after shadow soak | `src/travel_engine/trip_validator.py`, `findings.py`, `src/planner/tools/validate_itinerary.py` | Each finding has valid + deliberately invalid fixture; existing v6.1 checks retained | `pytest tests/travel_engine -k validator` | enforce off | Validator would call I/O |
| 4.7 | Replan integration: map finding → allowed REPLAN tool (`suggested_action` ⊂ existing replan tools); loops stay bounded; `dropped_stops` reasons recorded | `src/planner/tools/**`, `src/planner/graph/messages.py` | Max replan respected; no-progress ⇒ accept_partial | `pytest tests/planner -v` | flag off | Needs a new tool outside registry rules |

**Exit gate:** golden suite shows non-regression on all gates and improvement on ≥ 2 of {duplicate rate, schedule feasibility, coherence}; engine remains pure (architecture test green); legacy output identical with flags off.

### Slice 5 — Readiness V2, opening hours, ingestion quality (`READINESS_V2_ENABLED`)

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 5.1 | Readiness V2 per §8.2, pure function, same output envelope | `src/destinations/readiness.py`, `service.py` | Ten clustered places ⇒ `limited` for 3 days; boundary cases | `pytest tests/destinations -v` | flag off | Envelope change |
| 5.2 | Ingestion report script/endpoint-less: counts, distribution, dup rate, failures, freshness per destination | `scripts/`, `src/places/**` | Report on Darjeeling/Manali/Goa fixtures | run script | revert | — |
| 5.3 | Opening-hours parsing (preserve raw; `verified/unknown/malformed`) | `src/places/**`, `src/travel_engine/**` (consumes parsed struct) | Malformed/absent cases; no false "open" | `pytest tests/places tests/travel_engine` | flag off | Parser requires heavy dependency (ADR) |
| 5.4 | Retrieval eval on labeled must-include places (recall@k) added to gate | `evals/**`, `src/evaluation/metrics/**` | Recall metric hand-verified | `run_evals --replay --suite retrieval` | revert | — |

### Slice 6 — Canonical trip, map and guide (`CANONICAL_TRIP_V2_ENABLED`)

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 6.1 | Audit guide-agent + map data flow (read-only), write the canonical ID mapping | `docs/v8.2/**` | n/a | doc review | — | Guide agent uses names, not IDs (record; proceed to 6.2) |
| 6.2 | Guide suggestions carry canonical `place_id`; stop `status` (`confirmed`/`suggested`/`removed`/`user_added`); suggestions never auto-enter route | `src/trips/**`, `src/planner/**`, additive migration | Suggested ≠ routed; add-stop goes through controlled add endpoint | `pytest tests/trips -v` | flag off | Existing payload shape would break FE |
| 6.3 | Geometry provenance on day payload (`osrm`/`haversine_estimate`/`none`); GeoJSON unchanged shape (additive property) | `src/trips/service.py` | GeoJSON validity; fallback never labeled as road | `pytest tests/trips -k geojson` | flag off | — |
| 6.4 | Edit consistency: reorder/remove/add/reoptimize recompute schedule + legs + geometry, validate V2, rollback on failure, record `TripEditEvent` | `src/trips/service.py` | Failed edit leaves trip unchanged; markers/cards/geometry share IDs | `pytest tests/trips -v` | flag off | — |
| 6.5 | Optimistic concurrency **only if** audit shows last-write-wins is a real risk: `trips.version`, `If-Match`/expected-version, 409 on mismatch, additive for old clients | migration, `src/trips/**`, `docs/FE_guide.md` | Concurrent edit ⇒ 409; legacy client w/o version still works | `pytest tests/trips -k concurrency` | flag off | Cannot stay backward compatible (ADR) |
| 6.6 | FE integration tests: marker↔card selection, day highlight, edit round-trip, partial/degraded states | FE repo | FE CI | — | revert FE | No FE owner |

### Slice 7 — Experimental reasoning layer (flag, shadow, evidence-gated)

Entry criteria: S0–S6 shipped; S2 gate stable ≥ 2 weeks; judge promotion criteria (§11.8) evaluated.

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 7.1 | **Experience reasoner**: typed in/out (priorities over existing `place_id`s only), via `chat_completion`, validated; unknown IDs dropped; failure ⇒ skipped | `src/planner/reasoning/**` | Cannot introduce IDs/coords; malformed output ⇒ fallback; budget respected | `pytest tests/planner/reasoning` | `REASONING_LAYER_ENABLED=false` | Needs tool outside registry |
| 7.2 | **Critic (advisory)**: read-only input (request, area, evidence refs, canonical trip, deterministic findings); structured findings; no mutation; no repair trigger (`ORCHESTRATION_MAX_REPAIR_ATTEMPTS=0`) | same | Cannot override critical finding; judge outage ⇒ deterministic path unaffected | same | flag off | — |
| 7.3 | Shadow mode: sampled (`REASONING_SHADOW_SAMPLE_RATE`), no persistence, no response change, budget-capped; compare old vs new on quality, latency, cost | `src/planner/service.py`, `src/planner/reasoning/**` | Shadow cannot persist/alter response; cost cap enforced | integration test | sample rate 0 | Shadow doubles cost beyond cap |
| 7.4 | Decision: compare on golden + human-review set; ship only if §11.9 passes | docs | — | decision ADR | stay off | Does not meet gate ⇒ **do not ship** (a valid outcome) |

Budgets: ≤ `ORCHESTRATION_MAX_AGENT_INVOCATIONS` extra LLM calls, per-call deadline inside the 45 s ceiling, retry ceiling, cancellation, no-progress detection. No in-path repair loops. No additional roles without a new ADR. Slice 7 does not grow a hotel agent or a photo agent.

### Slice 9 — Guidebook enrich (`LODGING_V1_ENABLED`, `MEDIA_ENRICH_ENABLED`)

Entry: 6.2 shipped (canonical `place_id`, suggested versus routed). May run in parallel with Slice 7. Does not wait for §11.9. Both flags default off. Lodging HTTP and media HTTP run only after the trip is saved. Each external call uses an explicit timeout, tenacity retry, and a named fallback (empty suggestion list, or empty media list). A provider miss never fails generate and never becomes a 500. Provider notes and the guidebook layout live in the parent vault `docs/context/free-media-map-guidebook.md` (tripplanner root). Do not paste that catalog here.

| ID | Goal | Allowed paths | Required tests | Verify | Rollback | Stop if |
|---|---|---|---|---|---|---|
| 9.1 | Lodging ingest: Overpass `tourism=hotel\|guest_house\|hostel` inside the Slice 3 search area, through the existing place upsert, `category=lodging` | `src/geo/**` (query only), `src/places/**` | Hotel/guest_house/hostel map to lodging; attractions unchanged; empty Overpass ⇒ empty list | `pytest tests/geo tests/places -k lodging` | `LODGING_V1_ENABLED=false` | A new lodging table or a second place model |
| 9.2 | Stay suggestions on the saved trip. Rank by distance to the trip base, then to that day's cluster. Status `suggested`. Not route geometry | `src/trips/**`, `src/places/**` | Suggestion has `place_id` and `price_status=unknown`; suggestion is not a stop; outside search area ⇒ absent or disclosed fallback | `pytest tests/trips -k lodging` | flag off | Runs inside `POST /planner/generate` |
| 9.3 | Optional: user confirms one suggestion as the trip base; existing optimizer rebuilds the route. No auto-promote | `src/trips/**` | Confirm updates trip base and reoptimizes; declining leaves the route unchanged | `pytest tests/trips -k trip-base` | flag off | Confirmation runs inside generate |
| 9.4 | `src/geo/media/` facade. Order: OSM `image` tag, then Wikimedia, then OpenTripMap. Cache on `places.media` | `src/geo/media/**`, `src/places/**`, additive migration | Provider miss ⇒ empty list; missing attribution ⇒ not stored as showable; flag off ⇒ no HTTP | `pytest tests/geo -k media` | `MEDIA_ENRICH_ENABLED=false` | Import from `travel_engine/` or `planner/service.py`, or HTTP on generate |
| 9.5 | Proposed additive reads `GET /api/v1/places/{id}/media` and `GET /api/v1/trips/{id}/media`, each `ApiResponse`. Empty list when nothing resolved. Not folded into `PlaceOut` | `src/places/**` or media router, `docs/FE_guide.md` | Envelope; ownership; empty list; legacy place list unchanged | `pytest tests/places -k media` | flag off | Changes `PlaceOut`, SSE event names, or an existing path |
| 9.6 | Frontend contract: Stay block renders suggestions (unknown price and availability, no booking link). Stop shows media URL plus a visible credit, or the existing gradient when the list is empty | FE repo | FE CI | — | revert FE | No FE owner (halt 9.6 release; backend may stay dark) |

**Exit gate:** flag-off generate replay is byte-identical to baseline; suggestions are not stops; every shown photo has attribution; generate p95 stays ≤ 45 s.

### Slice 8 — Rollout and hardening

| ID | Goal | Verify |
|---|---|---|
| 8.1 | Dashboards: location resolution/ambiguity rate, search-area mismatch, duplicate rate, validator findings by code, replan rate, abort rate, p50/p95, tokens/cost, fallback rates, duplicate-persist attempts | Dashboards populated from traces + evaluation rows |
| 8.2 | Rollout: internal → shadow → limited beta → gradual; each stage gated by §11 numbers | Stage checklist signed off |
| 8.3 | Drills: flag rollback per feature, migration rollback, provider outage (Qdrant/OSRM/Nominatim/LLM down), SSE disconnect/reconnect, cancel | Drill log |
| 8.4 | Security review (§15) and cost controls (daily cap once baselines exist; production rate limits on Redis, not process memory) | Review doc |
| 8.5 | Legacy retirement decision — **not** automatic; requires a documented comparison | ADR |

---

## 10. Machine-enforced guardrails (CI, not prose)

All run on every PR (`tests/architecture/` + CI jobs). A failing guardrail blocks merge.

| # | Rule | Enforcement |
|---|---|---|
| G1 | `litellm`, `groq`, `openai` imported only in `src/core/llm/client.py` | AST/grep test |
| G2 | `src/travel_engine/**` imports no `geo`, `httpx`, `sqlalchemy`, `qdrant_client`, `litellm`, `requests`, `redis` | import-linter or AST test |
| G3 | No `os.environ` / `os.getenv` outside `src/config.py` | grep test |
| G4 | `planner/graph/nodes/**` imports no tool impl directly — only `execute_tool` | AST test |
| G5 | Routers import services only, not repositories/DB sessions | import-linter contract |
| G6 | `ToolContext` not referenced via module global/closure in graph builder | AST test + concurrency test (two simultaneous generates, isolated ctx) |
| G7 | Graph state TypedDict contains no `AsyncSession`/`RoutingProvider` | Type/field test |
| G8 | Legacy API/SSE snapshot contract unchanged (paths, envelopes, event names, GeoJSON shape) | `tests/snapshots` |
| G9 | New dependencies appear in `requirements.txt` with a why-comment | CI check on diff |
| G10 | Every Alembic revision has a working downgrade | CI migration up/down |
| G11 | All feature flags default to off/legacy | Settings test |
| G12 | Golden gate (replay mode) passes | `run_evals --replay` |
| G13 | Every flag-off run is byte-identical to baseline output on the snapshot suite | Differential test |
| G14 | Every `ValidationFinding.code` is in the stable registry; codes never removed | Registry test |
| G15 | Run status transitions only via the run service | AST test |
| G16 | `src/planner/service.py` and `src/travel_engine/**` do not import a lodging client or `src/geo/media/` | AST/grep test |

---

## 11. Evaluation specification (the gate)

### 11.1 Principles

1. Deterministic dimensions **gate**. Judge dimensions **inform**.
2. Do not blend deterministic and judge scores into one number until the judge is calibrated.
3. Assertions target structure and behavior, never exact LLM strings.
4. CI evals use recorded LLM fixtures (replay); live-model runs are a scheduled job and never block PRs on flakiness — but a live-job regression opens a blocking ticket.
5. Baselines change only via explicit `--update-baseline` in a reviewed PR.

### 11.2 Golden dataset minimums

| Item | Minimum |
|---|---|
| Destinations | ≥ 3 (Darjeeling, Manali, Goa; + 1 sparse-data town) |
| Total cases | ≥ 24 at S2 exit; ≥ 40 by S6 |
| Authorship | Case + expected assertions written/reviewed by a human; agents may propose, a human approves |
| Quarantine | Flaky/unclear cases flagged `quarantined`, excluded from gate, tracked with owner |

Composition (minimum counts):

| Case type | Count |
|---|---|
| Landmark vs city (same region) | 4 |
| Ambiguous names (multiple valid candidates) | 3 |
| Map pin + radius | 2 |
| Neighborhood / address base | 2 |
| Sparse data (small town) | 3 |
| Multi-day (3–5 days), varied pace/budget | 4 |
| Duplicate-prone attractions | 3 |
| Routing provider failure (haversine fallback) | 2 |
| LLM unavailable / malformed output | 2 |
| Long-distance / over-travel-budget | 2 |
| Missing/unknown opening hours | 2 |
| Guide-agent suggestion round-trip (S6) | 2 |

### 11.3 Deterministic gates (hard; all must pass)

| Metric | Gate |
|---|---|
| Critical findings in published trips | 0 |
| Duplicate stops | 0 |
| Invalid coordinates / missing place IDs | 0 |
| Route/schedule order mismatch | 0 |
| Non-chronological schedule | 0 |
| Stops outside search area (V2 path) | 0 |
| Every dropped stop has a reason | 100% |
| Every run terminal | 100% |
| Geo fallback on cases flagged `no_geo_fallback` | 0 |
| Flag-off differential vs baseline | identical |

### 11.4 Tolerance-banded metrics (regression = worse than band)

| Metric | Definition | Gate |
|---|---|---|
| Location-type accuracy | resolved `location_type` == labeled type | ≥ 95% on location cases |
| Ambiguity handling | ambiguous cases returning confirmation (not silent pick) | 100% |
| Search-area containment | fraction of selected stops inside `SearchArea` | ≥ 98% (target 100%) |
| Retrieval recall@10 | labeled must-include places in top 10 | ≥ baseline and ≥ 0.80 |
| Geographic coherence | per-day coordinate spread (existing validator measure) | not worse than baseline − tolerance |
| Schedule feasibility | days fitting active-time + travel caps | ≥ baseline; target 100% |
| p95 latency | replay with recorded latency model / live nightly | ≤ 45 s; ≤ baseline × 1.10 |
| Tokens/trip, LLM calls/trip | from usage capture | within §4 bounds |

Tolerances are set from baseline variance measured in S0.3 (run ×N); a metric with unmeasured variance cannot gate.

### 11.5 Layered evaluation map

| Layer | What | Gate or inform |
|---|---|---|
| Tool | correct tool for phase, valid args, fallback behavior, latency | Gate (precondition failure rate, wrong-phase = 0) |
| Location | type accuracy, ambiguity, containment | Gate |
| Retrieval | recall@k, fallback rate | Gate |
| Engine | dedup, coherence, feasibility, determinism | Gate |
| Persistence/map | one ID space, geometry↔order, edit round-trip | Gate |
| Preference/quality (judge) | relevance, diversity, narrative | Inform until promoted |
| User signals | saves, edits, removals, ratings | Inform; drives dataset growth |

### 11.6 Property / metamorphic tests (engine)

| Property | Statement |
|---|---|
| Determinism | Same input + same routing responses ⇒ identical output |
| Order invariance | Shuffling candidate input order does not change the selected set or day assignment |
| Idempotent dedup | `normalize(normalize(x)) == normalize(x)` |
| No-dup after removal | Removing any stop never creates a duplicate or breaks chronology |
| Monotonic coherence | Adding a distant place to a day never improves that day's coherence score |
| Budget respect | No day exceeds configured active-time and travel caps unless warning-flagged |
| Area respect | All stops lie within `SearchArea` |
| Schedule validity | Start times strictly non-decreasing; leg durations match `RouteLeg` |
| Flag equivalence | With V2 flags off, output equals pre-v8 output |

Use `hypothesis` only if justified (new package: `requirements.txt` + why-comment); otherwise parametrized fixtures with seeded randomness.

### 11.7 Human review protocol

| Item | Rule |
|---|---|
| Review set | ≥ 60 generated trips across ≥ 3 destinations, stratified by case type |
| Reviewers | ≥ 2 independent reviewers per trip; a third resolves disagreement |
| Rubric | Versioned rubric sheet (pass/fail per dimension + free-text); same dimensions as judge |
| Inter-rater agreement | Pairwise agreement on pass/fail ≥ 80% (else fix the rubric before judging the judge) |
| Cadence | Re-run on each rubric/prompt/model change and quarterly |

### 11.8 Judge promotion criteria (offline → advisory → gating)

| Stage | Entry criteria |
|---|---|
| Offline sampled | S2.6 shipped |
| Advisory in request path | Agreement with human consensus ≥ 80% on pass/fail **and** false-accept rate on human-failed trips ≤ 10% **and** judge p95 ≤ `EVALUATION_JUDGE_TIMEOUT_SECONDS` |
| Triggering repair | All of the above sustained over 2 consecutive review cycles **and** repair improves human-rated quality on a held-out set **and** repair never worsens deterministic metrics |

Judge model identity, prompt version and rubric version are stored with every judgment. Judge unavailability ⇒ `judge_unavailable` recorded; no claim of independent review is made.

### 11.9 Reasoning-layer ship gate (S7)

Ship (`REASONING_LAYER_ENABLED=true`) only if, on golden + human-review sets vs the current planner:

1. All §11.3 gates still pass.
2. Human-rated preference/quality improves by a pre-registered margin (set before running; e.g. ≥ +0.3 on a 5-point scale, or +10 pp pass rate) with confidence interval excluding zero.
3. p95 ≤ 45 s; tokens/cost within §4.
4. Failure/fallback rate no worse than baseline.

Otherwise the layer stays off. That outcome is acceptable and recorded in an ADR.

### 11.11 Guidebook honesty (S9, inform — does not gate itinerary quality)

| Check | Rule |
|---|---|
| Invented price or availability | 0. Slice 9 stays `unknown` |
| Suggestion without `place_id` | 0 |
| Suggestion outside the search area | Absent, or the fallback is disclosed |
| URL without attribution | 0 shown |
| Photo coverage | Not a gate. Low coverage is a pass |
| Flag-off generate replay | Byte-identical to baseline |

### 11.10 Persisted evaluation data

Extend, don't replace, `TripEvaluation` / `TripEditEvent`. Per generation record: run_id, flags in effect, workflow version, model/provider/fallback reason, prompt + rubric versions, tool trace (incl. ranking explanations), validator findings (code/severity/ids), search-area strategy + fallback flag, routing mode + fallback, tokens, retries, latency, terminal status. Evaluation HTTP endpoints stay out of scope until persistence + authorization contracts exist (current status: stub).

---

## 12. Model and provider strategy

| Phase | Rule |
|---|---|
| Now | Existing `LLM_MODEL` via LiteLLM is the only model. Optional role overrides default to it. |
| Benchmark before any change | Run golden set per candidate: itinerary quality, location accuracy, structured-output validity, tool-call reliability, p50/p95 latency, cost/trip, rate-limit and timeout failures |
| Fallback | Only an **approved, benchmarked** fallback model; else deterministic behavior/partial result. Record provider, model, fallback reason. Never switch silently |
| Note on other providers (e.g. Bedrock) | Possible later through LiteLLM only; verify regional availability, inference-profile requirements, tool-calling support, quotas, pricing, residency before use. Not a roadmap item |

Because the current model is a small free-tier model, structured-output validity and tool-call reliability are first-class benchmark metrics; any role needing reliable JSON must have a validated fallback path.

---

## 13. API, SSE and frontend compatibility

- Existing `/api/v1` paths, DTOs, SSE event names unchanged (guard G8). New fields are additive and optional.
- Candidate additive endpoints (only after S0 confirms the gap and FE agrees): `GET /planner/runs/{run_id}`, `POST /planner/runs/{run_id}/cancel`, `POST /locations/search|resolve|search-area`, `GET /trips/{id}/evaluation`, `POST /trips/{id}/feedback`.
- Proposed Slice 9 reads, same rule (not present until that slice ships): `GET /api/v1/places/{id}/media`, `GET /api/v1/trips/{id}/media`.
- **FE contract (S9):** the Stay block lists `LodgingSuggestion`s with unknown price and availability and no booking link. A stop photo shows the media URL and a visible credit. An empty media list keeps the non-photo fallback.
- SSE is delivery, not truth: add `run_id` in an additive event field, heartbeats, an explicit terminal event, and polling via run status for reconnect. A client disconnect cancels spend as today; a completed trip remains retrievable by `run_id`.
- **FE dependency (explicit):** S3 (location picker, type labels, radius control, area preview, anchor vs base), S6 (marker↔card sync, suggested vs confirmed, degraded/partial states, geometry provenance label), and S9.6 (Stay block, credited stop photos) need a named FE owner and contract tests before those slices release to users. Backend may ship dark behind flags without them.

---

## 14. Observability

Reuse structlog + Langfuse/NoOpTracer (keys empty ⇒ NoOp; errors swallowed). Add to the existing trace: `run_id`, trip id/version, flags in effect, location strategy, routing mode, validator findings by code, model/provider/fallback, prompt/rubric versions, tokens, retries, terminal status. Spans: run, location resolution, retrieval, engine, validation, (S7) reasoner/critic, persistence. Never log secrets or unnecessary personal data.

---

## 15. Security

- Retrieved text, provider descriptions, OSM tags, reviews, and image URLs are **untrusted data**, never instructions; delimit and sanitize before any LLM prompt.
- Wikimedia calls send `WIKIMEDIA_USER_AGENT` when that setting exists. A media proxy, if a later slice adds one, uses the same SSRF rules as other provider URLs.
- Tool allowlists (registry), Pydantic validation on every call, ownership enforcement (guest cookie must equal `Trip.session_id`), no cross-user leakage in run-status endpoints.
- Validate untrusted geometry (polygon/boundary) and clamp radii server-side; request/response size limits; SSRF protection on any provider URL handling; provider rate limits.
- No agent gets DB, shell, SQL or arbitrary-code access. No arbitrary-code sandbox is needed for this architecture; revisit only if such capabilities are introduced.
- Production rate limiting and caches must not depend on process-local memory (Redis in prod, as designed).

---

## 16. Explicitly deferred (revisit only on evidence)

Six-plus specialized agents; supervisor swarm; full durable checkpoint/resume, leases, workers; per-role mandatory model routing; automatic provider redundancy; in-path judge repairs; booking inventory, affiliate or referral links, live price, availability, image HTTP inside `POST /planner/generate`, unlabeled stock photos on a stop, Google Places; timezone-aware/seasonal/daylight scheduling (needs ADR §8.4); large trip-versioning redesign; microservices; cross-encoder rerank. Map satellite and outdoor styles stay in the parent media plan, not in this sequence.

Re-entry requires: measured demand or metric, an ADR, and a golden-suite extension covering the feature.

---

## 17. Coding-agent operating protocol

### 17.1 Preflight (every subslice)

1. Read `AGENT.md`, `docs/context.md`, this file, the relevant v6.1/v7 sections and `docs/FE_guide.md` when touching contracts.
2. Inspect real files/tests for the subslice's allowed paths; list existing contracts and reusable modules.
3. State any mismatch between this document and the repo **before** coding.
4. Post a short plan: files to touch (must be ⊆ allowed paths), tests to add, flag, rollback.
5. Confirm baseline suite is green before changes.

### 17.2 Rules during implementation

- One subslice per PR; smallest compatible change; no opportunistic refactors; no unrelated formatting churn.
- Touching files outside the subslice's allowed paths is a stop condition.
- No duplicate services/DTOs/repositories/LLM gateways; no invented modules or endpoints.
- New package ⇒ `requirements.txt` + why-comment; heavy package ⇒ ADR.
- Failure-path tests are written before claiming done.
- Behavior-changing code is behind its flag with the legacy path intact.

### 17.3 Completion requires

Implementation + unit tests + failure-path tests + (where applicable) integration tests + golden/replay gate run + snapshot suite green + guardrails green + docs and `docs/context.md` updated (verified facts only) + rollback described and tested. Claims of completion without test output are rejected.

---

## 18. Stop conditions (agent must halt and report, not improvise)

1. This document contradicts the repository or a locked contract → write ADR proposal; **halt that subslice until approved**.
2. The baseline suite is already red.
3. A change requires editing files outside the subslice's allowed paths.
4. A migration would be destructive or non-backward-compatible.
5. A legacy snapshot/SSE/GeoJSON contract would change.
6. The change needs a new provider SDK import outside the gateway, or I/O inside `travel_engine`.
7. A new package beyond what the subslice names is needed.
8. A golden/replay gate regresses and the cause is not the current change.
9. Latency would exceed the 45 s ceiling.
10. Required FE/product decision is missing (e.g., no FE owner, timezone scope).
11. Eval nondeterminism is discovered (fix reproducibility before proceeding).

---

## 19. Subslice completion report (mandatory template)

```markdown
## Subslice completion report
Slice / Subslice:
Branch / commit:
Flag(s) and default:

### Inspection
- Existing files/contracts inspected:
- Existing modules reused:
- Blueprint-vs-repo mismatches found:

### Changes
- Files changed (all within allowed paths? yes/no):
- New modules:
- Config/settings added:
- DB migrations (up/down tested?):
- API/SSE changes (additive only?):

### Validation
- Unit / integration / failure-path tests added:
- Commands run + results (paste output):
- Golden/replay gate result vs baseline (per metric):
- Snapshot suite + architecture guardrails:
- Flag-off differential identical to baseline?:

### Operations
- Timeouts / retries / fallbacks:
- Tracing/log fields added:
- Latency / token / cost delta vs baseline:

### Risk
- Known limitations:
- Rollback procedure (tested?):
- Follow-ups:

- [ ] Complete  [ ] Tests passing  [ ] Docs + context.md updated  [ ] Ready for integration
```

---

## 20. Definition of done for v8.3

v8.3 is complete when every v8.2 line below is true, and the two Slice 9 lines at the end are true:

- Location resolution is explicit and correct; search area, anchor and trip base are separate and traceable; no hidden universal radius.
- Published trips have zero critical deterministic findings, zero duplicate stops, valid coordinates, chronological, feasible schedules.
- Route geometry, itinerary order, markers, cards, guide suggestions and GeoJSON share one canonical ID space; fallback geometry is never presented as road geometry.
- Retries and reconnects never duplicate trips; every run reaches a terminal status and is queryable.
- Readiness reflects distribution and diversity, not only a count.
- Opening-hours claims exist only where verified; unknowns are represented as unknown.
- The golden suite (≥ 40 cases, ≥ 3 destinations) runs reproducibly in CI via replay, gates regressions with measured tolerances, and a human-reviewed set supports judge calibration.
- Every behavior change has a tested kill-switch; flag-off output equals baseline.
- Latency (p95 ≤ 45 s), token and cost targets are met against the S0 baseline.
- The reasoning layer is either shipped on evidence (§11.9) or documented as not worth shipping.
- Architecture guardrails (§10) are green in CI and the legacy API/SSE contract is unchanged.
- A generated trip can show suggested stays near the trip base with unknown price and availability, and those stays are not route stops.
- Each stop shows a credited free photo, or an honest empty state that keeps the non-photo fallback. Generate p95 remains ≤ 45 s.

---

## 21. ADR index (create as decisions are made)

| ADR | Decision |
|---|---|
| 001 | v8.2 stays a modular monolith |
| 002 | `/api/v1` backward compatibility; additive evolution |
| 003 | Bounded execution and loop prevention (planner + reasoning budgets) |
| 004 | Deterministic validator vs LLM judge responsibilities (N3, N9) |
| 005 | Anchor vs search area vs trip base; legacy mapping |
| 006 | Run tracking + idempotency scope (no checkpoint/resume) |
| 007 | Evaluation gates, tolerances, replay strategy |
| 008 | Judge promotion criteria |
| 009 | Opening-hours parsing approach |
| 010 | Timezone/date scope (deferred vs implemented) |
| 011 | Canonical trip ID space and stop status model |
| 012 | Trip versioning / optimistic concurrency (only if needed) |
| 013 | Reasoning-layer ship decision |
| 014 | Model/provider fallback policy |
| 015 | Lodging source and the unknown-price rule (S9) |
| 016 | Media facade, `places.media` cache, and attribution (S9) |

Each ADR: context, decision, alternatives, consequences, migration and rollback implications, status.

---

**One-line summary:** build the measurable, location-correct, deterministic core first; let the eval harness — not the architecture diagram — decide whether any agent layer earns its latency and cost. After that trip is saved, Slice 9 may attach suggested stays and credited photos. It is not an agent layer.
