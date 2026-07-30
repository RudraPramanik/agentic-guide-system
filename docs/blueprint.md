# Wandr — Blueprint Addendum: P4 Pre-Flight & Cross-Cutting Fixes
> Companion to `blueprint_final.md` (v6). This does NOT replace the blueprint — it captures
> what a full re-read surfaced right before P4 begins: one vocabulary bug that must be fixed
> in the very first P4 step, and several cross-cutting gaps (CORS, DB session lifecycle, SSE
> mechanics) that were never addressed at any phase and need a decision now, before they get
> built around implicitly.
> Treat every "LOCKED" section below as required input to the P4 (and eventually P5/P6) Cursor
> prompt docs — reference this file the same way those docs reference `AGENT.md`.

---

## Section A — Retroactive: applies to what's already shipped (P0–P3)

These don't require reopening P0–P3's code today, but they need a decision now because P4
onward (and P6 specifically) will be built assuming an answer either way.

### A.1 CORS — missing at every phase so far

No CORS middleware exists anywhere in the blueprint. The stated architecture is a separate
frontend (per the project's own Next.js-frontend precedent) calling this API — without CORS
configured, that simply doesn't work cross-origin, in dev or prod.

**LOCKED:** Add `CORSMiddleware` in `main.py`'s `create_app()`, registered alongside the
existing `RateLimitMiddleware`/`RequestLoggingMiddleware` stack. Origins come from
`get_settings().CORS_ALLOWED_ORIGINS: list[str]` (env-configurable, no hardcoded origin
strings — AGENT.md rule). Because P1's auth cookies (`wandr_token`, `wandr_session`) are
in play, `allow_credentials=True` is required, which means `allow_origins` **cannot** be
`["*"]` — it must be an explicit list.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### A.2 Cookie `SameSite` policy must be decided alongside CORS, not independently

P1's auth router sets `wandr_token` and `wandr_session` with `samesite="lax"`. This only
works if the frontend and backend are effectively same-site (same registrable domain, or a
reverse-proxied same-origin setup). If the frontend is deployed on a different domain/subdomain
than the API (common with, e.g., a Vercel frontend + a separate API host), `SameSite=Lax`
cookies will silently fail to attach to cross-site fetches even with CORS configured correctly.

**LOCKED — pick one before P6 builds anything cookie-dependent:**
- **Option A (recommended for MVP):** deploy frontend and backend under the same registrable
  domain (e.g., `app.wandr.dev` + `api.wandr.dev` behind a shared parent domain, or a single
  reverse-proxied origin). Keep `SameSite=Lax`.
- **Option B:** truly cross-site frontend/backend. Requires `SameSite=None; Secure=True`
  everywhere (breaks in local HTTP dev — needs a documented local-dev workaround), plus CORS
  `allow_credentials=True` with an exact origin match, no wildcard.

Whichever is chosen, write it into `docs/context.md` as a locked deployment decision — this
is not something to leave for whoever builds P6 to discover.

### A.3 Documentation drift: `pytest` install-order

The blueprint's Package Install Order table lists `pytest`/`pytest-asyncio`/`pytest-mock` at
step 7.3. The actual P1 build correctly installed them at step 1.11, since tests are needed
continuously from P1 onward — this was the right call, but it means the master blueprint
document itself is now stale on this point. Not a code change; update the table so the
blueprint stays a trustworthy reference rather than silently diverging from what was built.

---

## Section B — LOCKED for Step 4.2 (`travel_engine/travel_rules.py`): the vocabulary fix

This is the most important fix in this addendum, and it must land in the very first P4 step,
because everything else in P4 (`place_selector.py`, `day_allocator.py`, `schedule_builder.py`)
reads from `travel_rules.py`.

### The problem

Three vocabularies exist and the v6 blueprint's `travel_rules.py` draft conflates them under
one generic "category" naming convention:

| Vocabulary | Owner phase | Shape | Values |
|---|---|---|---|
| `Place.category` | P2 (Overpass ingestion, locked mapping) | single value, structural | `museum, viewpoint, monastery, attraction, park, trailhead` (`attraction` is the fallback for anything unmapped — likely the most common value in real data) |
| `Place.enriched_tags` | P3 (LLM enrichment) | list, interest-based | subset of `offbeat, photography, viewpoint, trek, monastery, cultural, family, nature, adventure` |
| `travel_rules.py` (v6 draft) | P4 | — | mixes both under generic names, with two concrete bugs |

**Concrete bugs this produces, as drafted:**
- `MORNING_ONLY_CATEGORIES` includes `"sunrise_point"` — P2's category mapping never produces
  this value. Dead config, will never fire.
- `VISIT_DURATION_BY_CATEGORY` has no entry for `"attraction"` (P2's own fallback category —
  the single most common value you'll actually see) or `"trailhead"`. Meanwhile it *does*
  have entries for `"trek"` and `"cultural"`, which are enriched-tag interest values that will
  **never** equal `place.category` for any place. Any code that does
  `VISIT_DURATION_BY_CATEGORY[place.category]` is one bad-luck POI away from a `KeyError`;
  `.get(place.category, ???)` just silently returns `None`/a wrong default instead.

### The fix — corrected `travel_rules.py`

**Rule going forward:** anything answering "what kind of PLACE is this, physically" is keyed
by `Place.category` (structural). Anything answering "does this place match what the user is
interested in" is keyed by `Place.enriched_tags` membership (interest). Overlap between the
two vocabularies (e.g. `"viewpoint"` and `"monastery"` legitimately exist in both) is fine and
intentional — a place can structurally BE a monastery and also be enriched-tagged
`"monastery"` for interest matching.

```python
# src/travel_engine/travel_rules.py

MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30
MAX_DAILY_TRAVEL_MIN = 180
DAY_START_TIME = "08:00"   # destination-local wall-clock time — intentionally timezone-naive.
                            # Itineraries are a local-time-of-day concept; do NOT convert to
                            # UTC or attach a timezone anywhere downstream of this.
LUNCH_BREAK_START = "13:00"
LUNCH_BREAK_MIN = 60

# ── STRUCTURAL constants — keyed by Place.category (P2's locked mapping) ──
# Every value P2 can ever produce MUST have an entry here, including the "attraction"
# fallback — it is P2's default category and will be common in real seeded data.
VISIT_DURATION_BY_CATEGORY: dict[str, int] = {
    "monastery": 45,
    "viewpoint": 20,
    "museum": 60,
    "park": 30,
    "trailhead": 90,
    "attraction": 40,   # was missing in the v6 draft
}
VISIT_DURATION_DEFAULT_MIN = 30   # last-resort fallback if a category ever falls outside
                                   # the dict above — belt-and-braces, should never actually
                                   # be hit if the dict stays in sync with Place.category

MORNING_ONLY_CATEGORIES: list[str] = ["viewpoint"]   # "sunrise_point" removed — P2 never
                                                       # produces this value; it was dead config
AVOID_SAME_DAY_PAIRS: list[tuple[str, str]] = [("monastery", "monastery")]

# ── INTEREST constants — keyed by Place.enriched_tags MEMBERSHIP (P3's controlled vocab) ──
# A place's score contribution is the SUM of weights for every tag that is BOTH in
# place.enriched_tags AND in the user's requested interests (see place_selector.py rule below).
CATEGORY_WEIGHTS: dict[str, float] = {
    "photography": 1.4, "offbeat": 1.3, "viewpoint": 1.2, "trek": 1.1,
    "cultural": 1.0, "family": 0.9, "monastery": 1.0, "nature": 1.1, "adventure": 1.2,
}
```

**Rule to lock in `place_selector.py` (step 4.3):** the scoring formula for multi-tag matches
must be stated explicitly, not left implicit:

```
score = sum(CATEGORY_WEIGHTS[tag] for tag in place.enriched_tags
            if tag in CATEGORY_WEIGHTS and tag in user_interests)
```

Sum, not max or average — a place matching two requested interests should outrank one
matching only one, which a max/average would obscure.

**Rule to lock in `day_allocator.py`/`schedule_builder.py` (steps 4.4/4.6):** visit duration
lookups always go through `.get(place.category, VISIT_DURATION_DEFAULT_MIN)`, never a bare
`[place.category]` subscript — defense in depth even with the dict now complete.

---

## Section C — LOCKED for the rest of P4

### C.1 `route_optimizer`'s ordering algorithm (step 4.5)

Unspecified in the v6 draft. **Lock it:** brute-force permutation search over the day's stops
(fixed start at `base_lat`/`base_lng`), evaluating all orderings via `routing.travel_matrix()`
and picking the lowest total travel time. `MAX_PLACES_PER_DAY = 6` caps this at 720
permutations — computationally trivial, fully deterministic, and avoids pulling in a
TSP-solver dependency that "lightest viable package" (blueprint principle #5) would otherwise
argue against. Do not let Cursor reach for `python-tsp` or similar here.

### C.2 `route_optimizer`'s drop-retry vs. REPLAN's `drop_weakest_stop` — coordinate them

Two layers can each remove stops from the same day with no visibility into what the other
already did: `route_optimizer`'s internal drop-retry (capped at 3 attempts, fires during the
PLAN phase if a day exceeds `MAX_DAILY_TRAVEL_MIN`) and `drop_weakest_stop` (a REPLAN-phase
tool, fires if `validate_itinerary` later finds the day lacks an anchor attraction — which
could be *because* the anchor was already dropped by the first mechanism).

**LOCKED:** `route_optimizer`'s output must record which stops (if any) were dropped and why,
surfaced on the day's data (e.g. a `dropped_stops: list[DroppedStop]` field with place name +
reason) so `validate_itinerary` and the REPLAN tools can see a day is already thinned before
deciding to drop further. When a day has already lost a stop to the PLAN-phase drop-retry,
`expand_poi_search` (broaden the candidate pool) is the better REPLAN choice than
`drop_weakest_stop` (thin it further) — this should be reflected in the agent's system prompt
guidance built in step 5.7, but the *data* to make that distinction needs to exist starting
in P4.

---

## Section D — LOCKED now, for P5/P6 to build against (decide before writing those docs)

### D.1 LangGraph state vs. `ToolContext` — keep non-serializable objects out of graph state

`AsyncSession` and `RoutingProvider` instances are not serializable and must never be part of
whatever `TravelState` LangGraph itself manages (and would checkpoint, if a checkpointer is
ever added). P4's function signatures already get this right —
`optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider)` takes routing as a
plain parameter rather than embedding it in a persisted state object. **The same discipline
must extend explicitly into P5:** `ToolContext(db, routing, state)` is constructed once per
graph invocation and threaded into node functions via closure/`RunnableConfig.configurable` —
it is NOT part of the `TravelState` TypedDict that LangGraph tracks as the graph's own state.
Write this down as a rule in P5's step 5.6, don't leave it to be discovered by trial and error
when someone tries to add a checkpointer later and it breaks.

### D.2 DB session lifecycle across the tool loop

Holding one `AsyncSession` open for an entire generation (up to `PLANNER_GENERATION_TIMEOUT_SECONDS`
= 45s, across up to 12 tool calls and several LLM round-trips) is a materially different load
profile than the short-lived request/response sessions everywhere else in the codebase.
Against P1's pool (`pool_size=10, max_overflow=20`), this exhausts far faster under concurrent
planner traffic than it would look like on paper.

**LOCKED — decide one before P5 builds the graph, don't improvise mid-build:**
- **Preferred:** acquire a session only inside the specific tools that actually need DB access
  (e.g. `search_places`'s PostGIS fallback, the final trip-save path), not once for the whole
  `ToolContext`. Most tools (`rank_places`, `build_route`, `build_schedule`, `validate_itinerary`)
  don't touch the DB at all — they operate on in-memory state.
- **Fallback if that's too invasive to retrofit:** measure actual pool exhaustion under
  realistic concurrent load before P6 ships, and size the pool explicitly for "long-held
  connections during LLM-bound requests," not the P1 defaults tuned for short web requests.

### D.3 SSE streaming — producer/consumer design, not "await then emit"

"Map `execute_tool` hooks to emit SSE events" + "wrap in `asyncio.wait_for`" under-specifies
*how* events reach the client while the graph is still running. The naive implementation
(await the full `graph.invoke()`, then emit everything) defeats SSE's purpose and makes the
endpoint feel frozen for up to 45 seconds.

**LOCKED design for step 6.2:**
```python
async def generate_stream(request: PlanRequest, ...):
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: str, data: dict):
        await queue.put((event, data))

    # graph runs as a background task; tool_executor hooks call emit() as they go
    task = asyncio.create_task(run_graph_with_emit(state, ctx, emit))

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():          # see D.4
                    task.cancel()
                    break
                try:
                    event, data = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
                if event in ("itinerary_done", "error", "clarification_needed"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```
The outer `PLANNER_GENERATION_TIMEOUT_SECONDS` ceiling wraps the background `task`, not the
generator — on timeout, cancel `task` and have the generator emit a final `error` event before
closing, rather than the connection just going silent.

### D.4 Client disconnect must stop server-side spend

Nothing in the v6 draft stops LLM/Qdrant calls from continuing after a client walks away
mid-stream (e.g. a mobile user backgrounding the app). Per D.3's sketch, poll
`request.is_disconnected()` in the streaming generator and cancel the background graph task
if the client is gone — this directly controls real LLM cost exposure, not just a UX nicety.

### D.5 Hard readiness floor before entering the tool loop

`check_readiness`'s warning-only behavior (below `PLANNER_MIN_READINESS_SCORE`, generation
still proceeds) is fine for the "limited" case, but a genuinely sparse/unseeded destination
(e.g. `place_count < 10`) will still burn up to 12 tool calls and real LLM spend before the
agent gives up — a slow, expensive failure instead of a fast, clear one.

**LOCKED:** add `PLANNER_ABSOLUTE_MIN_PLACES` (e.g. `10`) to settings. In `planner/router.py`,
check destination readiness *before* invoking the graph at all — if `place_count` is below
this floor, return a 409/422 with a clear "this destination isn't ready yet" message,
skipping the tool loop entirely. This is a cheap DB read that saves both LLM cost and user
wait time, and it's a strictly better UX than an eventual `abort_triggered=True` after 45s.

### D.6 Planner cache key must include accommodation location

`sha256(destination_id + sorted_interests + days + budget)` omits `base_lat`/`base_lng`, which
directly feeds `route_optimizer` — two requests with identical interests/days/budget but
different accommodation locations would incorrectly share a cached itinerary.

**LOCKED:** cache key includes `round(base_lat, 3)` and `round(base_lng, 3)` (bucketed to
~100m precision for reasonable hit rates without being so coarse it's wrong). Document
explicitly that caching is best-effort at the *parsed-preference* level — free-text nuance in
`raw_input` beyond what `parse_preferences` extracts (e.g. "avoid crowds," "vegetarian only")
is not reflected in the cache key and could be silently dropped on a cache hit. This is an
acceptable MVP tradeoff, but it should be a stated decision, not an accidental gap someone
discovers via a bug report.

### D.7 Anonymous trip ownership rule — write it down explicitly

"optional_auth + ownership" for guest trip access is implied but never stated as a rule
anywhere in the blueprint. **LOCKED for step 6.3/6.1:** for a guest (no auth token), ownership
means the `wandr_session` cookie value exactly matches `Trip.session_id` — mismatch or missing
cookie is a 403, identical treatment to an authenticated user hitting someone else's trip.
`session_id` is a `uuid.uuid4()` (P1), so this is not guessable — the rule just needs to exist
in writing before P6's trip router is built, not be inferred from the schema.

### D.8 `explain_selection()`'s output needs a defined landing spot

The blueprint says it's "logged to evaluation" but `TripEvaluation`'s schema has no field for
per-place selection explanations. **LOCKED:** route it through `tool_trace` instead of adding
a new `TripEvaluation` column — `rank_places`'s `ToolResult` can include a compact
`top_explanations: list[str]` (e.g. top 5) in its trace entry. Avoids a schema migration for
what is fundamentally debug/observability detail already covered by the generic
`tool_trace: list[dict]` JSONB column.

### D.9 Agent "nudge then default tool" mechanism — specify the actual mechanics

The Deterministic Fallback table says "No tool call after nudge → call default tool for
current phase," but the *nudge* itself is unspecified. **LOCKED for step 5.9:** on a
no-tool-call response, append a system-role message ("You must call one of the available
tools for this phase") to `build_agent_messages()` and retry `chat_with_tools()` once with
`tool_choice="required"` (not `"auto"`) on that specific retry. If it still returns no tool
call, execute the phase's documented default tool directly (bypassing the LLM for that step)
and increment a counter distinct from `tool_loop_count` so this failure mode is visible in
`tool_trace` separately from normal tool progress.

---

## Section E — Production hardening notes (not blocking, track for later)

- **Planner rate limit vs. sustained cost:** `10 req/min/IP` bounds burst abuse but not
  sustained daily spend — each generation is roughly 10+ LLM calls (parse_preferences +
  up to 12 tool-loop agent calls + write_narrative). Consider a coarser daily cap
  (per-IP or per-session) alongside the per-minute one once real usage patterns are known.
- **`/health` correctly stays DB-only** (consistent with the "Qdrant degrades gracefully,
  never fatal" philosophy elsewhere) — but there's currently no lightweight way for ops to
  see "Qdrant is degraded right now" without querying a specific destination's readiness.
  A `component_status` field on `/health` (`{"db": "ok", "qdrant": "degraded"}`) would help
  monitoring without changing the liveness/readiness semantics. Nice-to-have, not urgent.
- **No automated alerting on `abort_triggered` rate.** The blueprint documents this as
  something a human should investigate, but nothing computes or surfaces the rate over time.
  Fine for MVP; worth a P6+ follow-up once there's real traffic to alert on.

---

## Section F — Where each fix lands, mapped to blueprint step numbers

| Fix | Blueprint step(s) affected |
|---|---|
| B — vocabulary reconciliation (`travel_rules.py`) | **4.2** (must land here, first) |
| B — scoring formula, `.get()` defense | 4.3, 4.4, 4.6 |
| C.1 — route ordering algorithm | 4.5 |
| C.2 — drop-retry / REPLAN coordination | 4.5 (data shape), 4.7 (validator), 5.3 (REPLAN tools) |
| A.1/A.2 — CORS + cookie SameSite | Retroactive to P0/P1; must be resolved before P6 |
| D.1 — LangGraph state vs. ToolContext | 5.6 |
| D.2 — DB session lifecycle | 5.1–5.3 (tool implementations), measured before P6 ships |
| D.3 — SSE producer/consumer | 6.2 |
| D.4 — client disconnect handling | 6.2 |
| D.5 — hard readiness floor | 6.2 (pre-graph check) |
| D.6 — cache key fix | 6.4 |
| D.7 — anonymous trip ownership rule | 6.1, 6.3 |
| D.8 — `explain_selection` landing spot | 4.3 (emit into trace-shaped data), 5.10 (`record_evaluation`) |
| D.9 — agent nudge mechanism | 5.9 |
| A.3 — pytest doc correction | Documentation only, no code |