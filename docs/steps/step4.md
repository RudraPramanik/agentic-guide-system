# Wandr — P4 Cursor Prompts: Travel Engine (Intelligence Layer)
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P4 (5 days · 9 blueprint steps, expanded here to **4.0–4.10**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Layering (do not confuse):**
> - `docs/blueprint_final.md` = product / architecture source of truth
> - **this file** = Cursor build contract (sub-steps, failure boundaries, ✅ validation, tests)
> - OpenSpec = propose → apply → archive for **batched** implementation clusters (not one ceremony per micro-step)
>
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current ✅ validation passes.
>
> **Supersedes:** older `openspec/changes/p4-travel-engine` tasks that still cite pre-v6.1 `blueprint.md` language.
> Implement **from this prompt only**. Do not implement from stale OpenSpec tasks that contradict v6.1.

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | Structural `Place.category` conflated with interest `enriched_tags` → KeyError / dead duration keys | Split vocabularies (D1); complete P2 category durations; no `sunrise_point` |
| 2 | Scoring as max/avg hides multi-interest places | Score = **sum** of matching interest weights |
| 3 | TSP library or nearest-neighbor → nondeterministic / new package | Brute-force permutations ≤720; **no TSP package**; matrix once then score in memory |
| 4 | Drop-retry silent → P5 REPLAN over-thins | Surface `dropped_stops` with reasons |
| 5 | `explain_selection` becomes a DB column | Trace-shaped strings only (tool_trace / rank_places) |
| 6 | `geo/` imported inside `travel_engine/` | Protocols in engine; `OsrmRoutingProvider` adapter in `planner/` |
| 7 | CORS `*` + credentials | Explicit `CORS_ALLOWED_ORIGINS`; never wildcard with credentials |
| 8 | Wall-clock times converted to UTC in engine | Naive local strings only |
| 9 | Hard budget exclude without cost field | Soft preference only until a cost field exists |
| 10 | Magic geo-coherence threshold inline | `GEO_COHERENCE_MAX_STDDEV_KM` in `travel_rules.py` |

---

## Prerequisites (P3 must be complete)

Before step 4.0, confirm P3 from `docs/context.md`:

- All P3 steps ✅ — enrichment, Qdrant index, readiness `search_available` live
- `python -m pytest tests/ -v` passes (92+ tests)
- Seeded + enriched destination available for optional live checks (Darjeeling default)
- Current stubs (do **NOT** assume APIs exist — files are ~1-line placeholders):
  - `src/travel_engine/*.py` (all modules)
  - `src/planner/routing_provider.py`
  - `src/planner/tools/*` (full registry is P5 — P4 only adds a thin envelope)
- P2 `src/geo/osrm.py` is **real** — `get_route` with tenacity 2× → haversine × 1.4 fallback
- P3 `PLACE_TAG_VOCAB` in `src/places/constants.py` is **real** — every `CATEGORY_WEIGHTS` key MUST be ⊆ that vocab

## Prompt conventions (every step)

- **Extend, don't replace** P0–P3 code unless the step explicitly says replace.
- **Purity rule:** `src/travel_engine/` has **no** LLM, **no** network, **no** DB. No imports of `src.geo`, `httpx`, SQLAlchemy sessions, litellm, or Qdrant.
- **Geo gateway rule:** OSRM HTTP only in `src/geo/osrm.py`. Planner adapter wraps it; travel_engine never sees it.
- **Routing DI:** travel times enter the engine only via `RoutingProvider.travel_matrix(...)`.
- **Layering:** Router → Service → Repository for HTTP; P4 adds almost no new HTTP (CORS only). Tools stay stubs beyond the P4 envelope.
- **Time:** `datetime.now(timezone.utc)` only if a timestamp is required outside the engine. Schedule times are naive wall-clock **strings**.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **No new packages** without `requirements.txt` + why-comment. **No TSP solver package.**
- **Failure standards:** every code prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line.
- **OpenSpec cadence (implementation):** batch clusters — e.g. `4.0–4.2`, `4.3–4.4`, `4.5–4.6`, `4.7–4.8`, `4.9–4.10`. Do **not** run full propose→apply→archive for every single micro-step.

---

## P4 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         P4 dependency graph (canonical order)                │
└──────────────────────────────────────────────────────────────────────────────┘

  4.0 CORS (settings + CORSMiddleware)          ← parallel-safe; land first
        │
  4.1 protocols (RoutingProvider, RouteLeg)
        │
  4.2 travel_rules (constants as data)
        │
  4.3 place_selector ──► 4.4 day_allocator ──► 4.5 route_optimizer
                                                      │
                                                      ▼
                                              4.6 schedule_builder
                                                      │
                                                      ▼
                                              4.7 trip_validator
        │
  4.8 OsrmRoutingProvider (planner) + ToolResult / execute_tool skeleton
        │
  4.9 pytest ──► 4.10 smoke + context.md update

  Layer rules:
    travel_engine/*     → pure Python + Protocol; NEVER imports geo/httpx/DB/LLM
    planner/routing_*   → Adapter: wraps geo/osrm.py → RoutingProvider
    planner/tools stub  → ToolResult envelope; unknown tool → ok=False (never raise)
    FakeRoutingProvider → tests + smoke (no network)
```

**Canonical build order (the only order stated in this document):**
```
4.0 → 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → 4.10
```

---

## P4 design decisions (locked — no "optional" / either-or)

### Vocabulary split — LOCKED

| Concern | Keyed by | Owner |
|---------|----------|-------|
| Visit duration, morning-only, avoid-same-day pairs | `Place.category` (P2: `museum\|viewpoint\|monastery\|attraction\|park\|trailhead`) | `VISIT_DURATION_*`, `MORNING_ONLY_*`, `AVOID_SAME_DAY_PAIRS` |
| Interest scoring weights | Membership in `Place.enriched_tags` (P3 `PLACE_TAG_VOCAB`) | `CATEGORY_WEIGHTS` |

- Every P2 category MUST appear in `VISIT_DURATION_BY_CATEGORY`.
- Duration lookup: always `.get(category, VISIT_DURATION_DEFAULT_MIN)` — never bare `[category]`.
- `MORNING_ONLY_CATEGORIES = ["viewpoint"]` — **no** `sunrise_point`.
- Interest-only tags (`trek`, `cultural`, …) MUST NOT be duration-map keys.
- Every `CATEGORY_WEIGHTS` key MUST exist in `PLACE_TAG_VOCAB`.

### Scoring — LOCKED (sum)

```
score = sum(
    CATEGORY_WEIGHTS[tag]
    for tag in place.enriched_tags
    if tag in CATEGORY_WEIGHTS and tag in user_interests
)
```

Empty `enriched_tags` → score `0` (still selectable; do not crash).

### Budget — LOCKED soft

Until a per-place cost field exists: treat budget on the preferences object as a **soft preference** (may influence ranking/tie-break later). Do **not** invent a hard exclude.

### Route ordering — LOCKED (matrix once + permutations)

1. Call `routing.travel_matrix(waypoints)` **once** for the day's places plus a base sentinel waypoint `(BASE_SENTINEL_ID, base_lat, base_lng)`.
2. Provider MUST return a **full directed pairwise** `list[RouteLeg]` (every ordered pair i≠j).
3. Build an in-memory lookup `(from_id, to_id) → RouteLeg`.
4. Enumerate all permutations of the day's stops (≤ `MAX_PLACES_PER_DAY!` = 720). For each order, total travel =
   `leg(base → first) + sum(leg(stop_i → stop_{i+1}))`.
5. Pick minimum total travel. **No** `python-tsp` / OR-Tools / other TSP package.

### Drop-retry — LOCKED

If best total travel > `MAX_DAILY_TRAVEL_MIN`:
- Drop the **lowest-scored** remaining stop
- Record `{place_id, name?, reason}` on `dropped_stops`
- Retry optimization (max **3** drop attempts)
- Always return best-effort ordered stops + `dropped_stops` (may be empty)

### explain_selection — LOCKED

Return compact `str` for `tool_trace` / future `rank_places` `top_explanations`. **Not** a new `TripEvaluation` column / migration.

### Protocols vs adapter — LOCKED

- `RoutingProvider` + `RouteLeg` (+ optional tiny lookup helper) live in `src/travel_engine/protocols.py`.
- Prefer `list[RouteLeg]` over inventing `TravelTimeMatrix` unless a named type clearly helps the public API — default: **list + helper**.
- `OsrmRoutingProvider` in `src/planner/routing_provider.py` wraps `geo/osrm.get_route`. Map `RouteResult.fallback_used` → `RouteLeg.used_fallback`.

### Wall-clock times — LOCKED

`DAY_START_TIME`, lunch, `suggested_start_time` are destination-local **naive** `"HH:MM"` strings. travel_engine MUST NOT attach timezones or convert to UTC.

### Morning-only placement — LOCKED

Structural categories in `MORNING_ONLY_CATEGORIES` must land in stop order **≤ 2** with `suggested_start_time <= MORNING_SLOT_LATEST_START` (`"10:30"`).

### Geo coherence — LOCKED named constant

`GEO_COHERENCE_MAX_STDDEV_KM = 15.0` in `travel_rules.py` (hill-station / single-basin day). Validator compares sample std-dev of day stop coordinates (km) against this constant — no magic numbers in the check function body.

### Active day visit budget — LOCKED

```
ACTIVE_DAY_VISIT_BUDGET_MIN = 8 * 60 - MIN_TRAVEL_BUFFER_MIN   # 450 when buffer=30
CLUSTER_RADIUS_KM = 10.0
ANCHOR_MIN_SCORE = 0.7
MAX_ROUTE_DROP_ATTEMPTS = 3
BASE_SENTINEL_ID = UUID("00000000-0000-0000-0000-000000000000")  # routing base only; never a Place
```

### Design patterns (teaching + structure)

| Module | Pattern | Meaning |
|--------|---------|---------|
| `travel_rules` | Configuration as data | Constants, not buried conditionals |
| `place_selector` | Strategy-friendly pure API | Scoring/filter testable in isolation |
| `route_optimizer` | Template method + DI | Algorithm fixed; routing injected |
| `trip_validator` | Chain of responsibility | One function per named rule |
| `OsrmRoutingProvider` | Adapter | geo gateway → engine protocol |

### CORS + cookies — LOCKED

- `CORS_ALLOWED_ORIGINS: list[str]` via `get_settings()`; default includes `http://localhost:3000` for local Next.js.
- `CORSMiddleware(allow_credentials=True, allow_origins=<explicit list>)` — **never** `allow_origins=["*"]` with credentials.
- MVP deployment Option A: frontend + API same registrable domain → keep auth cookie `SameSite=Lax`. Document in `docs/context.md` at step 4.10 — **no auth cookie code change in P4**.

### Forward locks (design-only — do not implement in P4)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | `ToolContext` (db, routing) NOT in LangGraph `TravelState` | P5 |
| F2 | Prefer session-per-DB-tool over one session for 45s generation | P5 |
| F3–F5 | SSE queue, disconnect cancel, absolute min places | P6 |
| F6–F8 | Cache key rounding, guest ownership, agent no-tool nudge | P5/P6 |

---

## Step 4.0 — CORS middleware (pre-flight)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Add credentialed CORS with explicit origins from settings. This is step 4.0.
No travel_engine code yet. No new packages.

─── UPDATE src/config.py + .env.example ───

  CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

  # .env.example (JSON list — pydantic-settings):
  # CORS_ALLOWED_ORIGINS=["http://localhost:3000"]

─── UPDATE src/main.py create_app() ───

  from fastapi.middleware.cors import CORSMiddleware

  settings = get_settings()
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ALLOWED_ORIGINS,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # Order: add CORS before or with other middleware consistently; do not pair
  # allow_credentials=True with allow_origins=["*"].

─── RULES ───
- Origins come only from get_settings() — never hardcode production domains in main.py.
- Empty list = no cross-origin allow (safe default if misconfigured).
- Do not change JWT / cookie SameSite code in this step.

─── FAILURE BOUNDARY ───
Misconfigured CORS must not crash app startup. Must NOT: use wildcard origins with credentials.

─── VALIDATION ───
  python -c "
from src.config import get_settings
from src.main import create_app
s = get_settings()
assert isinstance(s.CORS_ALLOWED_ORIGINS, list)
assert '*' not in s.CORS_ALLOWED_ORIGINS
app = create_app()
print('PASS — CORS settings + app create')
"

  # Focused test (step 4.9 also covers): OPTIONS/preflight or TestClient request with
  # Origin: http://localhost:3000 → Access-Control-Allow-Origin echoes that origin.

✅ Failure path: settings list containing '*' with credentials design → reject in review;
   runtime must not ship that combo.
```

---

## Step 4.1 — travel_engine/protocols.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Define the routing injection surface. Pure types + Protocol only. This is step 4.1.

─── IMPLEMENT src/travel_engine/protocols.py ───

  from typing import Protocol
  from uuid import UUID
  from pydantic import BaseModel, Field

  class RouteLeg(BaseModel):
      from_place_id: UUID
      to_place_id: UUID
      duration_min: int
      distance_km: float
      used_fallback: bool = False

  class RoutingProvider(Protocol):
      async def travel_matrix(
          self, waypoints: list[tuple[UUID, float, float]]
      ) -> list[RouteLeg]:
          """
          Full directed pairwise legs for all waypoints (i != j).
          Never raises for 'no route' — adapters use geo fallbacks and set used_fallback.
          """
          ...

  def legs_to_lookup(legs: list[RouteLeg]) -> dict[tuple[UUID, UUID], RouteLeg]:
      """Index legs by (from_place_id, to_place_id). Last write wins on duplicates."""
      return {(leg.from_place_id, leg.to_place_id): leg for leg in legs}

─── RULES ───
- No geo/httpx/SQLAlchemy/litellm imports.
- Do not put OsrmRoutingProvider here (that is step 4.8).
- TravelTimeMatrix type is NOT required — list[RouteLeg] + legs_to_lookup is enough.

─── FAILURE BOUNDARY ───
This module has no I/O. Must NOT: import src.geo or perform network/DB calls.

─── VALIDATION ───
  python -c "
from src.travel_engine.protocols import RouteLeg, RoutingProvider, legs_to_lookup
from uuid import uuid4
a, b = uuid4(), uuid4()
leg = RouteLeg(from_place_id=a, to_place_id=b, duration_min=12, distance_km=3.5)
assert legs_to_lookup([leg])[(a, b)].duration_min == 12
print('PASS — protocols')
"

  # Import purity (Windows PowerShell):
  Get-ChildItem -Path src/travel_engine -Recurse -Filter *.py |
    Select-String "src\.geo|import httpx|litellm|qdrant|sqlalchemy"
  # Expected after 4.1: zero matches (stub files may still be empty placeholders — rewrite them as you go)

✅ Failure path: N/A for pure types — compile/import failure only.
```

---

## Step 4.2 — travel_engine/travel_rules.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Constants-as-data for the engine. Corrected v6.1 vocabulary. This is step 4.2.
🏗️ Configuration Object — rules are data, not logic.

─── IMPLEMENT src/travel_engine/travel_rules.py ───

  from uuid import UUID

  MAX_PLACES_PER_DAY = 6
  MIN_TRAVEL_BUFFER_MIN = 30
  MAX_DAILY_TRAVEL_MIN = 180
  DAY_START_TIME = "08:00"          # destination-local wall-clock; timezone-naive
  LUNCH_BREAK_START = "13:00"
  LUNCH_BREAK_MIN = 60
  MORNING_SLOT_LATEST_START = "10:30"
  ACTIVE_DAY_VISIT_BUDGET_MIN = 8 * 60 - MIN_TRAVEL_BUFFER_MIN  # 450
  CLUSTER_RADIUS_KM = 10.0
  GEO_COHERENCE_MAX_STDDEV_KM = 15.0
  ANCHOR_MIN_SCORE = 0.7
  MAX_ROUTE_DROP_ATTEMPTS = 3
  BASE_SENTINEL_ID = UUID("00000000-0000-0000-0000-000000000000")

  # ── STRUCTURAL — Place.category (P2) ──
  VISIT_DURATION_BY_CATEGORY: dict[str, int] = {
      "monastery": 45,
      "viewpoint": 20,
      "museum": 60,
      "park": 30,
      "trailhead": 90,
      "attraction": 40,
  }
  VISIT_DURATION_DEFAULT_MIN = 30
  MORNING_ONLY_CATEGORIES: list[str] = ["viewpoint"]
  AVOID_SAME_DAY_PAIRS: list[tuple[str, str]] = [("monastery", "monastery")]

  # ── INTEREST — Place.enriched_tags membership (P3 PLACE_TAG_VOCAB) ──
  CATEGORY_WEIGHTS: dict[str, float] = {
      "photography": 1.4,
      "offbeat": 1.3,
      "viewpoint": 1.2,
      "trek": 1.1,
      "cultural": 1.0,
      "family": 0.9,
      "monastery": 1.0,
      "nature": 1.1,
      "adventure": 1.2,
  }

  def visit_duration_min(category: str) -> int:
      return VISIT_DURATION_BY_CATEGORY.get(category, VISIT_DURATION_DEFAULT_MIN)

─── RULES ───
- Confirm CATEGORY_WEIGHTS.keys() ⊆ PLACE_TAG_VOCAB (import constants in a unit test, not here —
  travel_engine should not need to import places for production; tests may cross-check).
- No sunrise_point. No trek/cultural in VISIT_DURATION_BY_CATEGORY.

─── FAILURE BOUNDARY ───
Constants module — no I/O. Must NOT: conflate interest tags with structural categories.

─── VALIDATION ───
  python -c "
from src.travel_engine.travel_rules import (
    MAX_PLACES_PER_DAY, VISIT_DURATION_BY_CATEGORY, visit_duration_min,
    MORNING_ONLY_CATEGORIES, CATEGORY_WEIGHTS,
)
from src.places.constants import PLACE_TAG_VOCAB
assert MAX_PLACES_PER_DAY == 6
need = {'museum','viewpoint','monastery','attraction','park','trailhead'}
assert need <= set(VISIT_DURATION_BY_CATEGORY)
assert visit_duration_min('unknown_future') == 30
assert 'sunrise_point' not in MORNING_ONLY_CATEGORIES
assert set(CATEGORY_WEIGHTS) <= set(PLACE_TAG_VOCAB)
assert 'trek' not in VISIT_DURATION_BY_CATEGORY
print('PASS — travel_rules')
"

✅ Failure path: N/A — assertion failures mean the constants file is wrong; fix before continuing.
```

---

## Step 4.3 — travel_engine/place_selector.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Score + filter candidate places. Pure functions. This is step 4.3.
🏗️ Strategy-friendly pure API.

─── IMPLEMENT src/travel_engine/place_selector.py ───

  Use lightweight dataclasses / Pydantic models defined in this module (or a small
  travel_engine/schemas.py if you prefer one shared types file — either is fine;
  do not invent HTTP schemas).

  Required shapes (names may match closely):

  class PlaceCandidate:           # input — NOT the SQLAlchemy Place model
      id: UUID
      name: str
      category: str               # structural
      enriched_tags: list[str]
      lat: float
      lng: float

  class TripPreferences:
      interests: list[str]
      budget: str | None = None   # soft only in P4
      days: int = 3

  class ScoredPlace:
      place: PlaceCandidate
      score: float
      score_breakdown: dict[str, float]   # tag -> weight contributed

  def score_place(place: PlaceCandidate, interests: list[str]) -> tuple[float, dict[str, float]]:
      """Sum CATEGORY_WEIGHTS for tags in both enriched_tags and interests."""

  def explain_selection(place: PlaceCandidate, score_breakdown: dict[str, float]) -> str:
      """
      Compact one-liner for tool_trace, e.g.
      "Tiger Hill score=2.6 [photography=1.4, viewpoint=1.2]"
      """

  def select_places(
      candidates: list[PlaceCandidate],
      preferences: TripPreferences,
  ) -> list[ScoredPlace]:
      """
      1. Score each candidate (sum formula).
      2. Sort descending by score (stable tie-break: name or id).
      3. Apply AVOID_SAME_DAY_PAIRS as a selection-time conflict filter:
         when keeping two places would form a forbidden structural pair on the
         same eventual day pool, drop the lower-scored of the conflicting pair
         (document the exact greedy rule in a module docstring — locked: greedy
         keep-higher-score).
      4. Budget: soft only — do not hard-exclude.
      5. Return ScoredPlace list (may include score 0).
      """

─── RULES ───
- Do not import SQLAlchemy Place — map at the tool/service boundary later (P5).
- Morning-only is NOT enforced here (schedule_builder + validator).

─── FAILURE BOUNDARY ───
No I/O. Empty candidates → []. Empty interests → all scores 0, still returns list.
Must NOT: raise KeyError on unknown category/tag; unknown tags simply contribute 0.

─── VALIDATION ───
  python -c "
from uuid import uuid4
from src.travel_engine.place_selector import PlaceCandidate, TripPreferences, select_places, explain_selection

def cand(name, cat, tags):
    return PlaceCandidate(id=uuid4(), name=name, category=cat, enriched_tags=tags, lat=27.0, lng=88.0)

prefs = TripPreferences(interests=['photography','offbeat'])
multi = cand('A', 'viewpoint', ['photography','offbeat'])
single = cand('B', 'museum', ['photography'])
empty = cand('C', 'park', [])
scored = select_places([multi, single, empty], prefs)
assert scored[0].place.name == 'A'
assert scored[0].score > scored[1].score
assert any(s.place.name == 'C' and s.score == 0 for s in scored)
print(explain_selection(multi, scored[0].score_breakdown))
print('PASS — place_selector')
"

✅ Failure path: N/A — pure function; bad prefs should not raise.
```

---

## Step 4.4 — travel_engine/day_allocator.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Split scored places into per-day lists under caps + visit-time budget. This is step 4.4.

─── IMPLEMENT src/travel_engine/day_allocator.py ───

  def allocate_days(
      selected: list[ScoredPlace],
      days: int,
      preferences: TripPreferences | None = None,
  ) -> list[list[ScoredPlace]]:
      """
      Returns exactly `days` lists (some may be empty only if not enough places —
      prefer filling days round-robin / cluster-first as below).

      Rules:
      - Each day: len(places) <= MAX_PLACES_PER_DAY
      - Each day: sum(visit_duration_min(p.place.category)) <= ACTIVE_DAY_VISIT_BUDGET_MIN
      - Geographic pre-clustering: places within CLUSTER_RADIUS_KM of each other
        prefer the same day (haversine pure-python helper local to this module —
        NOT geo/osrm).
      - Higher scores preferred when a day is full.
      """

─── RULES ───
- Haversine for clustering distance is allowed as pure math inside travel_engine
  (no HTTP). Do not call src.geo.
- Use visit_duration_min() from travel_rules — never bare dict [].

─── FAILURE BOUNDARY ───
days < 1 → treat as 1 OR raise ValueError — LOCKED: raise ValueError("days must be >= 1").
Overflow places that cannot fit → omitted from result (log via return size; no I/O logger required,
but document in docstring). Must NOT: put >6 places on a day.

─── VALIDATION ───
  python -c "
from uuid import uuid4
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.day_allocator import allocate_days

def mk(i, cat='attraction'):
    p = PlaceCandidate(id=uuid4(), name=f'P{i}', category=cat, enriched_tags=[], lat=27.0+i*0.01, lng=88.0, )
    return ScoredPlace(place=p, score=float(20-i), score_breakdown={})

selected = [mk(i) for i in range(18)]
days = allocate_days(selected, 3)
assert len(days) == 3
assert all(len(d) <= 6 for d in days)
from src.travel_engine.travel_rules import visit_duration_min, ACTIVE_DAY_VISIT_BUDGET_MIN
for d in days:
    total = sum(visit_duration_min(s.place.category) for s in d)
    assert total <= ACTIVE_DAY_VISIT_BUDGET_MIN
print('PASS — day_allocator', [len(d) for d in days])
"

✅ Failure path: days=0 → ValueError (assert in a tiny test in 4.9).
```

---

## Step 4.5 — travel_engine/route_optimizer.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Order a day's stops for minimum travel; drop-retry with dropped_stops. This is step 4.5.
🏗️ Template method + RoutingProvider DI.

─── IMPLEMENT src/travel_engine/route_optimizer.py ───

  class DroppedStop(BaseModel):
      place_id: UUID
      name: str | None = None
      reason: str

  class OptimizeResult(BaseModel):
      ordered: list[ScoredPlace]          # or list[PlaceCandidate] — keep ScoredPlace
      legs: list[RouteLeg]                # consecutive legs for the chosen order (base→first, …)
      total_travel_min: int
      dropped_stops: list[DroppedStop] = Field(default_factory=list)
      still_over_budget: bool = False

  async def optimize_route(
      day_places: list[ScoredPlace],
      base_lat: float,
      base_lng: float,
      routing: RoutingProvider,
  ) -> OptimizeResult:
      """
      1. If day_places empty → empty OptimizeResult.
      2. Build waypoints = [(BASE_SENTINEL_ID, base_lat, base_lng), *places].
      3. matrix = await routing.travel_matrix(waypoints)  # ONCE per attempt
      4. lookup = legs_to_lookup(matrix)
      5. Brute-force permutations of day_places; score total travel via lookup.
      6. If best total > MAX_DAILY_TRAVEL_MIN and drops < MAX_ROUTE_DROP_ATTEMPTS:
            drop lowest score; append DroppedStop(reason="exceeded_max_daily_travel");
            retry from step 2 with remaining places.
      7. Return best available; still_over_budget=True if still over after max drops.
      """

─── ALSO: tests helper (can live in tests/ support module) ───

  class FakeRoutingProvider:
      """Deterministic; no network. Implements travel_matrix with a provided dict
      of (from_id, to_id) -> (duration_min, distance_km) or a duration function."""

─── RULES ───
- Never import src.geo.
- No TSP packages.
- Missing lookup edge → treat as large penalty OR rebuild matrix — LOCKED: Fake and Osrm
  providers MUST return the full pairwise set so lookup always hits; if missing in
  production adapter bug, treat duration as 10**9 and set still_over_budget path.

─── FAILURE BOUNDARY ───
routing.travel_matrix failures: Protocol adapters must not raise for route miss.
If the provider raises unexpectedly, optimize_route may propagate — adapters (4.8)
MUST catch geo failures. Unit tests use Fake only.

─── VALIDATION ───
  python -c "
import asyncio
from uuid import uuid4, UUID
from src.travel_engine.travel_rules import BASE_SENTINEL_ID
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.route_optimizer import optimize_route

class Fake:
    async def travel_matrix(self, waypoints):
        # asymmetric: force a known best order
        ids = [w[0] for w in waypoints]
        legs = []
        for a in ids:
            for b in ids:
                if a == b: continue
                # default 30; make BASE->A and A->B and B->C cheap when order A,B,C
                dur = 30
                legs.append(RouteLeg(from_place_id=a, to_place_id=b, duration_min=dur, distance_km=1.0))
        return legs

async def main():
    places = []
    for name in ['A','B','C']:
        p = PlaceCandidate(id=uuid4(), name=name, category='attraction', enriched_tags=[], lat=0.0, lng=0.0)
        places.append(ScoredPlace(place=p, score=1.0, score_breakdown={}))
    result = await optimize_route(places, 0.0, 0.0, Fake())
    assert len(result.ordered) == 3
    print('PASS — route_optimizer basic', [s.place.name for s in result.ordered])

asyncio.run(main())
"

✅ Failure path: over-budget fixture in 4.9 must assert dropped_stops non-empty and reasons set.
```

---

## Step 4.6 — travel_engine/schedule_builder.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Assign naive wall-clock start times + lunch + morning-only enforcement. This is step 4.6.

─── IMPLEMENT src/travel_engine/schedule_builder.py ───

  class ScheduledStop(BaseModel):
      place: PlaceCandidate
      score: float
      visit_duration_min: int
      suggested_start_time: str          # "HH:MM"
      arrival_note: str | None = None

  def build_day_schedule(
      ordered_stops: list[ScoredPlace],
      route_legs: list[RouteLeg],
  ) -> list[ScheduledStop]:
      """
      - Start at DAY_START_TIME.
      - For each stop: suggested_start_time = running clock; then add visit_duration_min;
        then add travel to next from matching consecutive route_legs.
      - If adding the next visit would cross LUNCH_BREAK_START, insert LUNCH_BREAK_MIN gap
        (arrival_note may mention lunch).
      - After initial timing, if any MORNING_ONLY stop is outside slots 1–2 or starts
        after MORNING_SLOT_LATEST_START, reorder morning-only into early slots and
        recompute times (document algorithm: stable extract morning-only to front,
        preserving relative order among them, max 2 early slots).
      - Never attach timezone / UTC conversion.
      """

─── RULES ───
- Durations via visit_duration_min(category).
- Pure function — no LLM, no I/O.

─── FAILURE BOUNDARY ───
Empty ordered_stops → []. Mismatched legs length: if legs are consecutive for
base→s0, s0→s1, … then len(legs) == len(stops) (including base→first). Document and
assert; on mismatch raise ValueError with clear message (domain error, not HTTP).

─── VALIDATION ───
  # Build a 6-stop day including one viewpoint; assert times and morning slot.
  # (Full script deferred to pytest 4.9 — minimum here:)
  python -c "
from src.travel_engine.schedule_builder import build_day_schedule
print('PASS — schedule_builder import', build_day_schedule)
"

✅ Failure path: mismatched legs → ValueError (tested in 4.9).
```

---

## Step 4.7 — travel_engine/trip_validator.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Chain-of-responsibility validation rules. This is step 4.7.
🏗️ Chain of Responsibility — each rule is a separate function.

─── IMPLEMENT src/travel_engine/trip_validator.py ───

  class ValidationResult(BaseModel):
      passed: bool
      warnings: list[str] = Field(default_factory=list)
      errors: list[str] = Field(default_factory=list)

  # Input itinerary shape — lock a simple structure:
  class DayPlan(BaseModel):
      stops: list[ScheduledStop]
      total_travel_min: int
      dropped_stops: list[DroppedStop] = Field(default_factory=list)

  class TripItinerary(BaseModel):
      days: list[DayPlan]

  def check_daily_travel_cap(itinerary: TripItinerary) -> list[str]: ...
  def check_no_repeat_places(itinerary: TripItinerary) -> list[str]: ...
  def check_morning_slots(itinerary: TripItinerary) -> list[str]: ...
  def check_anchor_per_day(itinerary: TripItinerary) -> list[str]:
      """Each day needs at least one stop with score > ANCHOR_MIN_SCORE."""
  def check_geo_coherence(itinerary: TripItinerary) -> list[str]:
      """Per-day coordinate stddev (km) <= GEO_COHERENCE_MAX_STDDEV_KM."""

  def validate_trip(itinerary: TripItinerary) -> ValidationResult:
      errors: list[str] = []
      warnings: list[str] = []
      for check in (
          check_daily_travel_cap,
          check_no_repeat_places,
          check_morning_slots,
          check_anchor_per_day,
          check_geo_coherence,
      ):
          errors.extend(check(itinerary))
      # If any day already has dropped_stops, add a warning hint for P5 REPLAN
      # (prefer expand_poi_search) — warning, not error.
      if any(d.dropped_stops for d in itinerary.days):
          warnings.append(
              "one_or_more_days_already_dropped_stops_prefer_expand_poi_search"
          )
      return ValidationResult(passed=not errors, warnings=warnings, errors=errors)

─── RULES ───
- Specific error messages per rule (include day index / place name when useful).
- No I/O. No REPLAN tool calls.

─── FAILURE BOUNDARY ───
Bad itinerary → errors list, not exceptions (except programmer ValueErrors on None input —
LOCKED: None itinerary raises TypeError/ValidationError from Pydantic).

─── VALIDATION ───
  python -c "
from src.travel_engine.trip_validator import validate_trip, TripItinerary, DayPlan
good = TripItinerary(days=[])  # empty trip: define locked behavior —
# LOCKED: empty days → passed=True with warning OR errors — choose: warnings=['empty_itinerary'], passed=True
print('import ok', validate_trip)
"

  # Real assertions in 4.9: good fixture errors=[]; injected repeat + late viewpoint → distinct errors.

✅ Failure path: validator never raises on merely-invalid travel plans — only returns errors.
```

**Empty itinerary lock (clarified):** `days == []` → `ValidationResult(passed=False, errors=["empty_itinerary"])`.

---

## Step 4.8 — planner/routing_provider.py + tools envelope stub

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Adapter + minimal tool envelope for P5. This is step 4.8.
🏗️ Adapter Pattern — geo stays outside travel_engine.

─── IMPLEMENT src/planner/routing_provider.py ───

  class OsrmRoutingProvider:
      async def travel_matrix(
          self, waypoints: list[tuple[UUID, float, float]]
      ) -> list[RouteLeg]:
          """
          For every ordered pair (i != j):
            result = await get_route([(lat_i, lng_i), (lat_j, lng_j)])
            append RouteLeg(..., duration_min=round(result.duration_min),
                            distance_km=result.distance_km,
                            used_fallback=result.fallback_used)
          Never raise httpx to callers — get_route already falls back.
          """

─── IMPLEMENT minimal tools envelope ───

  Prefer extending existing stub files rather than inventing a parallel tree:

  src/planner/tools/schemas.py  — ToolResult model at minimum:
    class ToolResult(BaseModel):
        ok: bool
        code: str | None = None
        message: str | None = None
        data: dict | None = None

  src/planner/tools/registry.py — skeleton:
    async def execute_tool(name: str, input: BaseModel | dict, ctx: object | None = None) -> ToolResult:
        """
        P4: if name not in a minimal registry dict (may be empty or placeholder keys):
            return ToolResult(ok=False, code="unknown_tool", message=...)
        Never raise.
        Full PHASE_TOOLS / 12-tool registry is P5 — do not implement tool bodies here.
        """

─── RULES ───
- OsrmRoutingProvider is the ONLY P4 module that imports src.geo.osrm.
- travel_engine must still have zero geo imports after this step.
- Do not implement LangGraph, SSE, or real tools.

─── FAILURE BOUNDARY ───
OSRM down → get_route haversine fallback → used_fallback=True on legs.
Unknown tool → ToolResult(ok=False), never exception.

─── VALIDATION ───
  python -c "
import asyncio
from uuid import uuid4
from src.planner.routing_provider import OsrmRoutingProvider
from src.planner.tools.registry import execute_tool
from src.planner.tools.schemas import ToolResult
from pydantic import BaseModel

class Empty(BaseModel):
    pass

async def main():
    r = await execute_tool('no_such_tool', Empty())
    assert isinstance(r, ToolResult) and r.ok is False
    # Optional live: two nearby Darjeeling coords — may use public OSRM
    print('PASS — tools envelope + provider import')

asyncio.run(main())
"

  Get-ChildItem -Path src/travel_engine -Recurse -Filter *.py |
    Select-String "src\.geo|import httpx"
  # Expected: zero matches

✅ Failure path: unknown tool → ok=False; OSRM failure → fallback legs (not 500).
```

---

## Step 4.9 — P4 pytest coverage

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Expand pytest for the travel engine + CORS + purity. This is step 4.9.

─── CREATE / EXTEND ───

  tests/travel_engine/test_travel_rules.py
  tests/travel_engine/test_place_selector.py
  tests/travel_engine/test_day_allocator.py
  tests/travel_engine/test_route_optimizer.py
  tests/travel_engine/test_schedule_builder.py
  tests/travel_engine/test_trip_validator.py
  tests/travel_engine/test_purity.py          # no geo/httpx imports under travel_engine
  tests/planner/test_routing_provider.py     # Fake + fallback flag mapping (mock get_route)
  tests/planner/test_execute_tool_stub.py
  tests/core/test_cors_middleware.py         # Origin allow headers

─── REQUIRED CASES (minimum) ───

  ★ rules: duration keys ⊇ P2 set; default duration; CATEGORY_WEIGHTS ⊆ PLACE_TAG_VOCAB
  ★ selector: multi-interest outranks single; empty tags score 0; conflict pair drops lower
  ★ allocator: 18 places / 3 days → 3 lists ≤6 and within visit budget; days=0 → ValueError
  ★ optimizer: FakeRoutingProvider optimal order; over-budget → dropped_stops with reason;
               no python-tsp in requirements
  ★ schedule: 6-stop day with viewpoint in slot 1–2; first >= 08:00; lunch gap when spanning 13:00
  ★ validator: good fixture errors=[]; repeat place error; late viewpoint error; empty_itinerary
  ★ cors: configured origin echoed; reject design of * + credentials (assert settings)
  ★ purity: AST or string scan — travel_engine has no src.geo / httpx / litellm / qdrant

─── VALIDATION ───
  python -m pytest tests/travel_engine tests/planner/test_routing_provider.py tests/planner/test_execute_tool_stub.py tests/core/test_cors_middleware.py -v
  python -m pytest tests/ -v

✅ Failure path: failing tests block 4.10 — do not update context.md as complete.
```

---

## Step 4.10 — P4 smoke script + context.md

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Real end-to-end proof without LangGraph + update context after green. This is step 4.10.

─── CREATE scripts/test_p4_smoke.py ───

  """
  P4 smoke — run: python scripts/test_p4_smoke.py
  Sections (print headers; exit 1 on first failure — never ambiguous PASS):
    1) travel_rules constants
    2) select_places on fixture candidates
    3) allocate_days
    4) optimize_route with FakeRoutingProvider
    5) build_day_schedule
    6) validate_trip (expect passed on constructed good plan)
    7) execute_tool unknown → ok=False
    8) import guard: travel_engine has no geo
    9) OPTIONAL_LIVE_OSRM=1 → OsrmRoutingProvider pairwise for 3 waypoints (skip if unset)
  """

─── UPDATE docs/context.md (ONLY after smoke + full pytest pass) ───

  - Last updated / Next step → P5.1
  - Progress rows 4.0–4.10 ✅
  - Implemented modules: travel_engine/*, OsrmRoutingProvider, ToolResult/execute_tool stub, CORS
  - Stubs list: remove travel_engine purity stubs; keep planner graph/tools bodies as stubs
  - Deployment note: MVP Option A — same registrable domain; auth cookies stay SameSite=Lax
  - Do NOT claim P5 complete

─── FAILURE BOUNDARY ───
Network down during optional live OSRM → skip or fail that section only if OPTIONAL_LIVE_OSRM=1;
default run must PASS offline via Fake.

─── VALIDATION ───
  python scripts/test_p4_smoke.py
  python -m pytest tests/ -v

  Get-ChildItem -Path src/travel_engine -Recurse -Filter *.py |
    Select-String "src\.geo|import httpx|litellm|qdrant_client"
  # Expected: zero matches

✅ Failure path: smoke exits non-zero with clear section header — not "PASS" on partial failure.
```

---

## P4 Complete — Full Verification Checklist

Before claiming P4 done in `docs/context.md`:

```bash
# ── Unit / integration ──
python -m pytest tests/ -v

# ── Smoke (offline Fake) ──
python scripts/test_p4_smoke.py

# ── Optional live OSRM ──
# OPTIONAL_LIVE_OSRM=1 python scripts/test_p4_smoke.py

# ── Import guards (PowerShell) ──
Get-ChildItem -Path src/travel_engine -Recurse -Filter *.py |
  Select-String "src\.geo|import httpx|litellm|qdrant_client|sqlalchemy"
# Expected: zero matches

# No TSP package sneaked in:
Select-String -Path requirements.txt -Pattern "tsp|ortools|python-tsp"
# Expected: zero matches

# CORS: no wildcard in default settings
python -c "from src.config import get_settings; s=get_settings(); assert '*' not in s.CORS_ALLOWED_ORIGINS; print('CORS ok', s.CORS_ALLOWED_ORIGINS)"

echo "P4 COMPLETE — proceed to P5"
```

### P4 ship criteria

| Check | Expected |
|-------|----------|
| `travel_engine` purity | No geo/httpx/LLM/DB imports |
| Vocabulary | Structural durations ⊇ P2 categories; interest weights ⊆ `PLACE_TAG_VOCAB` |
| Scoring | Sum of matching weights; empty tags → 0 |
| Route order | Brute-force ≤720; matrix once; no TSP package |
| Drop-retry | `dropped_stops` with reasons; max 3 |
| Schedule | Naive `"HH:MM"`; morning-only slots 1–2; lunch gap |
| Validator | Per-rule errors; empty itinerary fails; dropped_stops → warning |
| Adapter | `OsrmRoutingProvider` in planner; fallback → `used_fallback` |
| Tools stub | Unknown tool → `ok=False`, never raise |
| CORS | Explicit origins + credentials; never `*` |
| SameSite | Documented Option A in context.md; no cookie code change |
| pytest + smoke | Green; smoke fails loud by section |

### Recommended OpenSpec implementation batches

After this prompt is archived, implement with batched changes (example):

1. `4.0–4.2` — CORS + protocols + rules  
2. `4.3–4.4` — selector + allocator  
3. `4.5–4.6` — optimizer + schedule  
4. `4.7–4.8` — validator + adapter/envelope  
5. `4.9–4.10` — pytest + smoke + context.md  

Do **not** open a full propose→archive cycle for each single micro-step unless a design conflict appears.
