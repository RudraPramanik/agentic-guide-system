## Context

P6.0 persists per-stop `leg_polyline` onto `TripPlace.polyline`. P6.1 delivers `TripRepository` / `TripService` (`save_from_state`, `assert_can_access`, `claim_for_user`) and `TripOut` schemas. P6.2 SSE generate auto-saves trips and returns `trip_id`. `src/trips/router.py` is still a ~1-line stub; `main.py` registers planner but not trips.

Step contract: `docs/steps/step6.md` §6.3. SoT: `docs/blueprint_final.md` v6.1 (CRUD + GeoJSON; step6 v2 restores claim HTTP). AGENT.md: Router → Service → Repository; JSON endpoints use `ApiResponse` / `PaginatedResponse`; no litellm/geo httpx/redis in trips.

**Prerequisite gate (verified this propose):** context Next → P6.3; routes show `/api/v1/planner/generate` only; trips service/repo/schemas/exceptions real; router stub.

## Goals / Non-Goals

**Goals:**

- `TripService.build_geojson` producing a valid GeoJSON FeatureCollection from DB-loaded trip data.
- Thin service methods for HTTP: get (404), list-by-user (paginated), soft-delete, claim wrapper that loads + policy + returns `TripOut`.
- Full trips router + registration: list/get/geojson/delete/claim per locked auth matrix.
- Pure polyline decode (no new package) so LineStrings use OSRM road geometry.
- Focused tests for ownership 403, claim 200/403/409, geojson LineString-when-present / Points-only degradation.
- Update `docs/context.md` Progress 6.3 → Next P6.4 after green.

**Non-Goals:**

- Redis / planner cache (6.4).
- P6 ship smoke / full suite stamp / P6-complete context (6.5).
- P7 edit/replan routes.
- Persisting `day_polyline` (no column; reconstruct from legs).
- Changing SSE generate or `save_from_state` field map.
- Making GeoJSON require auth (LOCKED public).

## Decisions

### D1 — Thin router; service owns policy + GeoJSON

**Choice:** Router only: auth deps, cookie read (`COOKIE_SESSION` from auth router), call `TripService`, map to envelopes / 204 / raw GeoJSON. Service methods:

| Method | Behavior |
|--------|----------|
| `get_for_access(trip_id, *, user_id, session_id) → Trip` | `get_with_places` or `TripNotFoundError`; then `assert_can_access` |
| `list_for_user(user_id, params) → (items, total)` | `list_by_user` + `TripOut` mapping |
| `soft_delete_for_user(trip_id, user_id)` | load + assert (auth required upstream) + `repo.soft_delete` + commit |
| `claim_trip(trip_id, user_id, session_id) → Trip` | load + `claim_for_user` |
| `build_geojson(trip) → dict` | pure FeatureCollection builder |

**Alternatives:** Router calls repo directly — rejected (AGENT.md). Put GeoJSON in router — rejected (harder to unit test; service already has loaded trip).

### D2 — GeoJSON shape (LOCKED degradation)

**Choice:** `FeatureCollection` with:

1. **Point** features — one per `TripPlace` with coords from joined Place (`to_shape`); properties: `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id` (only fields available from DB/schemas — no invented travel metrics beyond what's already on TripPlace).
2. **LineString** features — prefer **one per day** by concatenating decoded coords from that day's stop polylines in `order_in_day` order (dedupe shared endpoints). If a day has no decodable polylines, omit LineString for that day (Points remain). Alternate acceptable: one LineString **per leg** (`properties.day`, `order`); pick day-level concatenation as default for cleaner geojson.io renders.

**Coordinate order:** GeoJSON `[lng, lat]`. Encoded polyline decode yields `(lat, lng)` — swap on emit.

**Decode:** Small pure Google-encoded polyline decoder in `src/trips/` (e.g. `_decode_polyline` private or `geojson_util.py`). Invalid/empty string → skip that leg (never raise). **No** `import polyline` package; **no** live `geo.osrm` / httpx.

**Alternatives:** Stop-to-stop straight LineStrings without decode — rejected (throws away P6.0 road geometry). Add `polyline` package — rejected (AGENT.md no new packages without need; decoder is ~40 lines).

### D3 — Public GeoJSON vs ownership (LOCKED)

**Choice:** `GET .../geojson` is **public** (no auth, no session check). Missing/soft-deleted trip → `TripNotFoundError` (404). This matches step6 auth matrix and enables shareable map links. CRUD get still enforces ownership.

**Trade-off:** Anyone with a trip UUID can see place names/coords/route. Acceptable for MVP (UUIDs are unguessable enough; no PII beyond itinerary content). Hardening later (signed URLs / auth) is post-MVP — do not invent in 6.3.

### D4 — DELETE auth asymmetry (LOCKED, comment in code)

**Choice:** DELETE uses `require_auth` + ownership even though GET allows guest session ownership. Comment in router: intentional — no anonymous destructive actions. Soft-delete via `BaseRepository.soft_delete` (Trip has SoftDeleteMixin); commit in service.

### D5 — Claim HTTP error surface

**Choice:** Router does **not** catch claim errors. `TripForbiddenError` / `TripAlreadyClaimedError` / `TripNotFoundError` propagate to the global `WandrError` handler (403 / 409 / 404). Claim requires `require_auth` + `wandr_session` cookie; missing cookie → treat as session mismatch → 403 (via service) or raise Unauthorized if auth dep fails first.

### D6 — List scope

**Choice:** `GET /trips` lists **only** `list_by_user(current_user)` — authenticated user's trips (including claimed). No guest list endpoint in 6.3 (guests use get-by-id with matching session). Matches step6.

### D7 — Envelope exception for GeoJSON

**Choice:** GeoJSON returns the FeatureCollection dict/JSON directly (`response_class=JSONResponse` or typed dict return), **not** wrapped in `ApiResponse`. Document in router docstring as intentional map-tool exception (same spirit as SSE frames ≠ ApiResponse). All other trips JSON endpoints use envelopes.

### D8 — No migration / no model changes

**Choice:** No Alembic. Relationships from 6.1 are sufficient. Do not add `day_polyline` column.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Encoded polyline decode bugs → empty LineStrings | Unit-test decoder with known fixture; Points still render; treat decode fail as degrade |
| Public geojson UUID leakage | Accept for MVP; UUID opacity; no soft-deleted trips returned |
| Router accidentally imports redis/httpx | Import guard in validation; keep decode pure |
| Claim without session cookie after login | Document: frontend must retain `wandr_session` across OAuth; service 403 if missing/mismatch |
| `day_polyline` absent → fragmented legs | Day-level concat of leg polylines; document expected shape |
| Double-commit patterns | Follow AuthService / existing claim: service owns commit |

## Migration Plan

1. Implement service GeoJSON + helpers → router → register in `main.py`.
2. Run step6.3 path assertion + focused pytest.
3. Update `docs/context.md` (6.3 ✅, Next P6.4, live trips endpoints, remove trips HTTP from stubs).
4. Rollback: unregister router / revert files — no DB migration to reverse.

## Open Questions

None blocking. Optional post-MVP (not this change): auth-gated GeoJSON; persist aggregate `day_polyline`; rate-limit public geojson.

## Hardening suggestions (folded into decisions above)

1. **Pure polyline decode** — required for honest LineStrings without a new dependency.
2. **Day-level LineString concat** — better geojson.io UX than N leg features.
3. **Decode/None degradation** — never 500 when OSRM was down at generate time.
4. **DELETE comment** — prevent future “fix” of intentional auth asymmetry.
5. **Retain `wandr_session` after login** — claim depends on it; call out in context.md when applying.
6. **Do not** add P7 edit routes or Redis here even if tempting after CRUD lands.
