# Wandr P2 Guide — Geo Foundation

> **Audience:** engineers implementing P2, and anyone explaining Wandr’s backend in interviews.  
> **Phase:** P2 — first external I/O + PostGIS spatial APIs after P1’s DB/auth foundation.  
> **Build prompts:** [`docs/steps/step2.md`](../steps/step2.md) (v2 hardened) · **Checkpoint:** [`docs/context.md`](../context.md) · **Guardrails:** [`AGENT.md`](../../AGENT.md)

This guide is **knowledge**, not a Cursor paste prompt. For implementation, follow `step2.md` in order.

---

## 1. Where P2 sits in Wandr

| Phase | Focus | P2 dependency |
|-------|--------|----------------|
| P0 | Scaffold, config, LLM gateway, FastAPI | Already done |
| P1 | Models, BaseRepository, auth, middleware, pytest | **Prerequisite** |
| **P2** | **Geo gateways, seed POIs, destinations/places APIs, readiness** | **You are here** |
| P3 | Enrich + Qdrant index | Needs seeded places |
| P4–P5 | travel_engine + agent tools | Needs OSRM + places + readiness |
| P6–P7 | Planner SSE API, trips, edits | Needs all of the above |

**P2 product outcome:** you can geocode a city, scrape POIs, store them in PostGIS, list them via HTTP, and report how “ready” a destination is for planning — still without LLM trip generation.

```
User / CLI
   │
   ├─ seed_destination.py ──► geocoder ──► Nominatim
   │                      └──► overpass ──► Overpass API
   │                      └──► PlaceRepository upsert ──► Postgres/PostGIS
   │
   ├─ GET /destinations/search ──► DestinationService (cache-aside)
   ├─ GET /places?destination_id= ──► PlaceService
   └─ GET /destinations/{id}/readiness ──► compute_readiness() [pure]
```

---

## 2. Backend context (what already exists vs what P2 builds)

### Already real (P1) — do not rebuild

| Piece | Why P2 needs it |
|-------|-----------------|
| `Destination`, `Place` models | Tables + PostGIS `POINT` + denormalized counters |
| `BaseRepository` | Soft-delete, paginate, flush-only writes |
| `ApiResponse` / `PaginatedResponse` | Envelope for new routers |
| `WandrError` / `NotFoundError` | Map geo misses → 404 |
| Auth + rate-limit middleware | Extend path limit for `/destinations/search` |
| pytest + `wandr_test` | Mocked geo tests + API tests |
| `httpx`, `tenacity`, `shapely`, `geoalchemy2` | Already in `requirements.txt` |

### Still stubs until P2 code lands

`src/geo/*`, `src/destinations/{repository,service,router,schemas,readiness}`, `src/places/{repository,service,router,schemas}` — one-line placeholders today. **Do not invent APIs from memory;** implement from `step2.md`.

### Live endpoints after P2 (target)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/destinations/search?q=` | DB-first; Nominatim on miss |
| GET | `/api/v1/destinations/{id}/readiness` | Score + tier |
| GET | `/api/v1/places?destination_id=` | Paginated |
| GET | `/api/v1/places/{id}` | Single place |

---

## 3. Engineering knowledge (P2 deep dive)

### 3.1 Layering (non-negotiable)

```
Router → Service → Repository → DB
              │
              └── may call src/geo/ only from Service or scripts
```

| Rule | Meaning |
|------|---------|
| Geo gateway | Nominatim / Overpass / OSRM HTTP **only** inside `src/geo/` |
| No OverpassQL in services | Call `fetch_pois(...)`; never build query strings in scripts beyond args |
| Repos flush, services commit | Same as `AuthService` |
| Routers return envelopes | `ApiResponse[T]` or `PaginatedResponse[T]` — never raw ORM |

### 3.2 Patterns introduced or reinforced in P2

| Pattern | Where | Interview one-liner |
|---------|-------|---------------------|
| **Gateway** | `geo/geocoder`, `overpass`, `osrm` | One module owns an external API; callers never see URLs/QL |
| **Cache-Aside** | `DestinationService.search` | Read DB → miss → fetch Nominatim → write DB → return |
| **Resilience contract** | All three geo clients | Explicit timeout + tenacity retry + named fallback |
| **Atomic upsert** | Place + Destination by OSM id | `INSERT … ON CONFLICT DO UPDATE … RETURNING` — no check-then-insert race |
| **Denormalized counters** | `Destination.place_count` etc. | Seed/enrich/index scripts own counters; geocode upsert must not touch them |
| **Pure function** | `compute_readiness` | No I/O; easy unit tests; service supplies counts |

### 3.3 Resilience contracts (law)

| Module | Retry | Fallback |
|--------|-------|----------|
| Geocoder | 3×, exp 1–8s | `None` → service raises `DestinationNotFound` 404 |
| Overpass | 3×, exp 2–16s | `[]` → seed continues / dest with 0 places |
| OSRM | 2×, fixed 1s | Haversine × 1.4, `fallback_used=True` |

Retry **only** on connect/timeout (and LLM rate-limit elsewhere). **Never** retry 4xx.

httpx: always `Timeout(connect=…, read=…, write=…, pool=…)` — never bare `timeout=10`.

### 3.4 PostGIS pitfalls that interviewers love

1. **`ST_MakePoint(lng, lat)`** — longitude first. Swapping silently places Darjeeling in the ocean.
2. **Geometry vs geography** — SRID 4326 *geometry* distances are in **degrees**. Radius in km **must** cast both sides to `geography` and use meters (`radius_km * 1000`).
3. **Soft-delete on Place** — radius/list queries must exclude `deleted_at IS NOT NULL` (via `BaseRepository` filters).

### 3.5 Async cache correctness

**Wrong:** `@functools.lru_cache` on `async def geocode` — caches the *coroutine object*; second await crashes.

**Right:** process-local `dict` of **resolved** `GeocodedPlace | None`, guarded by `asyncio.Lock`. Cache confirmed misses too (don’t re-hit Nominatim for known nonsense queries).

**Known limit:** cache + 1 req/sec throttle are **per-process**. Multi-worker → fragmented cache / per-worker Nominatim budget. Upgrade path: Redis at P6 (same as rate-limiter backend).

### 3.6 Readiness scoring (P2 acceptance)

```text
place_score   = min(place_count / 100, 1.0)
enriched_pct  = enriched_count / place_count   (0 if no places)
indexed_pct   = indexed_count / place_count    (0 if search unavailable)
score         = 0.4*place_score + 0.35*enriched_pct + 0.25*indexed_pct
tier          = ready ≥0.7 | limited ≥0.3 | sparse <0.3
```

**After seed only (no enrich/index):** ~144 places → score ≈ **0.4**, tier **`limited`**. Blueprint’s “ready after seed” is amended — `ready` needs P3.

### 3.7 Canonical build order

```text
2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → 2.5 → 2.6c → 2.6c′ → 2.7a → 2.7b → 2.8 → 2.9 → 2.10
```

Seed (2.4) needs destination atomic upsert from 2.6b. OSRM (2.5) is parallel for P4/P5 but stays in the linear path.

### 3.8 External data sources (what they are)

| Source | Role in Wandr | Policy / care |
|--------|---------------|---------------|
| **Nominatim** | Geocode city names → lat/lng + OSM place id | Valid `User-Agent` with contact; ≤1 req/sec |
| **Overpass** | Scrape tourism/park/trailhead POIs in a radius | Slow reads OK (30s); empty list on failure |
| **OSRM** | Driving route distance/duration/polyline | Public demo OK for MVP; haversine fallback |
| **OpenStreetMap** | Underlying map data for all three | Attribution / fair use; don’t hammer public endpoints |

---

## 4. Interview Q&A (P2-flavored)

Use these as **spoken answers**. Tie each to Wandr when possible.

### Architecture & design

**Q: Why a Gateway for Nominatim instead of calling it from the service?**  
**A:** Isolates URL, headers, timeouts, retries, and parsing in one place. Services call `geocode(query)`; if we swap providers or add Redis cache, callers don’t change. Same idea as our LLM client being the only `litellm` import.

**Q: Explain Cache-Aside on destination search.**  
**A:** Hot path reads Postgres. On miss we call Nominatim, persist a `Destination` row, return it. Second search for “Darjeeling” should not log an outbound geocode. We still rate-limit the HTTP route because a miss storm can amplify Nominatim load.

**Q: Router → Service → Repository — why so strict?**  
**A:** Keeps HTTP concerns (status codes, envelopes) out of persistence, and SQL out of routers. Testable services; repositories stay flush-only so transactions stay explicit at the use-case boundary.

**Q: Why denormalize `place_count` on Destination?**  
**A:** Readiness and catalog UIs need fast counts without `COUNT(*)` on every request. Trade-off: writers (seed/enrich/index) must update counters carefully; geocode upsert must never zero them out on conflict.

### Resilience & async

**Q: What’s a resilience contract?**  
**A:** For every external call: explicit connect/read timeouts, tenacity policy, and a **named** fallback (`None`, `[]`, haversine). External failure must not become an opaque 500.

**Q: Why not retry on HTTP 400/404?**  
**A:** Those are client/logic errors; retrying burns quota and delays failure. We retry transient network failures only.

**Q: Why is `@lru_cache` wrong on async functions?**  
**A:** It caches the coroutine returned by calling the function, not the awaited result. First await consumes it; later “hits” raise. Use a dict of resolved values (or `cachetools`/`async-lru` designed for async).

**Q: How do you handle concurrent inserts of the same OSM id?**  
**A:** Don’t SELECT-then-INSERT. Use one `INSERT … ON CONFLICT (osm_id) DO UPDATE … RETURNING` so two workers can’t both “think” the row is missing.

### Spatial / PostGIS

**Q: Geometry vs geography for radius search?**  
**A:** With lon/lat SRID 4326, geometry `ST_DWithin` uses degrees. For “30 km around Darjeeling” we cast to geography and pass meters so the unit matches human intent.

**Q: Why lng before lat in `ST_MakePoint`?**  
**A:** PostGIS follows x,y → longitude, latitude. Lat-first is a classic silent bug.

**Q: Soft deletes and spatial queries?**  
**A:** Soft-deleted places must be filtered; otherwise deleted POIs still appear in radius results and pollute itineraries later.

### Product / readiness

**Q: What does destination readiness mean?**  
**A:** A 0–1 score from place coverage, enrichment %, and index %. Planner can warn below a threshold but still generate. After seed-only, tier is `limited`; `ready` needs enrichment + indexing (P3).

**Q: Why seed from Overpass instead of a static CSV?**  
**A:** Real destinations need live OSM coverage; seed is re-runnable via upsert. Partial POI failures log and continue so one bad element doesn’t abort the city.

### Testing

**Q: How do you test geo without hitting the network in CI?**  
**A:** Unit-test gateways with mocked `_fetch_nominatim` / `_post_overpass` / `_call_osrm`. Keep a smoke script for real Nominatim/Overpass when network is allowed. Assert failure paths: `None`, `[]`, `fallback_used=True`.

**Q: What would you ask in a PR review for P2?**  
**A:** Geo only in `src/geo/`? Timeouts set? Atomic upsert? Geography cast? Destination existence → 404? Counters not clobbered on geocode upsert? Rate limit on search? Failure-path tests present?

---

## 5. Quick cheat sheet

| Topic | Answer in one line |
|-------|--------------------|
| Geo entry | Only `src/geo/` |
| Geocode fail | `None` → 404 at API |
| Overpass fail | `[]` |
| OSRM fail | Haversine × 1.4 |
| Point order | `(lng, lat)` |
| Radius units | `geography` + meters |
| P2 readiness | `limited` after seed |
| Build order | See §3.7 / `step2.md` |
| Async cache | Dict of values, not `lru_cache` on `async def` |

---

## 6. Related project docs

| Doc | Use when |
|-----|----------|
| [`docs/steps/step2.md`](../steps/step2.md) | Implementing each P2 prompt + validation |
| [`docs/context.md`](../context.md) | What’s done / stubs / next step |
| [`docs/app/system.md`](system.md) | Whole-system architecture |
| [`docs/app/lld.md`](lld.md) | Named patterns and principles |
| [`docs/blueprint_final.md`](../blueprint_final.md) | Resilience contracts, phase plan |
| [`docs/spec.md`](../spec.md) | OpenSpec think → propose → apply workflow |
| [`AGENT.md`](../../AGENT.md) | Hard coding guardrails |
| [`openspec/specs/p2-step-doc/spec.md`](../../openspec/specs/p2-step-doc/spec.md) | Locked P2 step-doc requirements |

---

## 7. Books & external references

Curated reading list (links + how they map to P2): **[`docs/books/p2-references.md`](../books/p2-references.md)**

Index of all book/reference packs in this repo: **[`docs/books/README.md`](../books/README.md)**
