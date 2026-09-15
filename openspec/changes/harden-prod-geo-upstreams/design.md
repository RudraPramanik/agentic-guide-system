## Context

See `proposal.md` — Why. Today `geocode()` collapses Nominatim 403 into `None`, destinations search maps `None` → 404, and the process cache stores that `None`, so Oracle prod looks like “no destinations” while auth/Redis/Qdrant/OSRM work. Geo I/O stays in `src/geo/`; errors use existing `ExternalServiceError` (502).

## Goals / Non-Goals

**Goals:**
- Distinguish policy/rate Nominatim failures from true misses at geocode + search HTTP layers.
- Stop negative-caching 4xx policy failures.
- Support Nominatim-compatible commercial endpoints via existing URL setting + optional API key.
- Harden Overpass request headers slightly; document prod geo ops clearly.

**Non-Goals:**
- Multi-provider geocode abstraction / failover chain in code.
- Self-hosted Nominatim/Photon.
- Redis-backed geocode cache.
- FE contract updates in this change (note BREAKING 404→502 in proposal only).
- Changing OverpassQL template or POI category map.

## Decisions

### 1. Raise `ExternalServiceError` from geocoder on 403/429 (not a Result type)

- **Choice:** On Nominatim HTTP 403 and 429, raise `ExternalServiceError(service="nominatim", ...)`. Other 4xx (e.g. 400 malformed) may also raise the same error for consistency; empty `200 []` stays `None`.
- **Why:** Matches existing auth/LLM pattern; global exception handlers already map `ExternalServiceError` → 502 envelope. Destination service only needs try/except or let-it-propagate.
- **Alternatives:** `(GeocodedPlace | None, error)` tuple — more churn; keep all 4xx as `None` — preserves misleading 404.

### 2. Do not cache `ExternalServiceError` outcomes

- **Choice:** Only write cache on success (`GeocodedPlace`) or confirmed empty (`None` after 200 with no hits / soft failures). Never cache after raising.
- **Why:** Operators fixing UA or `NOMINATIM_BASE_URL` should not need API restart for every previously typed query.
- **Alternatives:** Short TTL cache for failures — more complexity than needed for MVP.

### 3. Optional `NOMINATIM_API_KEY` as query `key`

- **Choice:** Empty default; when set, add `params["key"]=settings.NOMINATIM_API_KEY`. Document LocationIQ-style base URL override.
- **Why:** Minimal change; many Nominatim forks use `key`. Header-based vendors can be a follow-up if needed.
- **Alternatives:** Vendor-specific clients — out of scope.

### 4. Overpass: add `Accept: application/json`

- **Choice:** Always send with existing User-Agent. Keep 4xx → empty elements behavior (prepare/seed already degrade).
- **Why:** Oracle probe saw 406; Accept + real UA is the cheapest mitigation. Full multi-mirror failover stays ops (`OVERPASS_API_URL` + `PLACES_SOURCES`).

### 5. Docs over code for Overpass/source order

- **Choice:** Blueprint + `.env.production.example` + `docs/vps.md` instruct real UA, provider swap, and `PLACES_SOURCES=opentripmap,geoapify` when Overpass is blocked. No automatic source reordering in code this change.
- **Why:** Keys/mirrors are operator choices; avoid surprising local-dev defaults.

## Resilience Contracts

| Path | Timeout | Retry | Failure behavior |
|------|---------|-------|------------------|
| Nominatim search | connect 5 / read 10 | 3× on Timeout/Connect only | 403/429 → `ExternalServiceError`; empty/soft → `None` |
| Search HTTP budget | `SEARCH_GEOCODE_TIMEOUT_SECONDS` | n/a | timeout → 404; `ExternalServiceError` → 502 |
| Overpass | connect 10 / read 90 | 3× on Timeout/Connect | 4xx → `[]` (unchanged) |

## Risks / Trade-offs

- [FE treats any search failure as empty] → Mitigation: document BREAKING 502; FE can show “geo service unavailable” vs “no match”.
- [Other 4xx mapped to 502 may be over-broad] → Mitigation: start with 403/429 explicitly in implementation; extend only if tests need it.
- [Accept header may not fix all Overpass 406s from datacenter IPs] → Mitigation: ops docs for mirrors / drop overpass from `PLACES_SOURCES`.
- [Commercial Nominatim may differ slightly on `addressdetails`] → Mitigation: keep existing parse; spike against chosen vendor during apply if URL changes.

## Migration Plan

1. Ship code + env template/docs.
2. On VPS: set real `NOMINATIM_USER_AGENT`; if still 403, set `NOMINATIM_BASE_URL` (+ `NOMINATIM_API_KEY`) to a compatible provider.
3. Restart API (clears any old negative cache from pre-fix image).
4. Smoke: `GET /destinations/search?q=London` → 200 or (if still blocked) **502** not silent 404.
5. Rollback: revert image; behavior returns to 404-for-all-misses (worse UX but previous contract).

## Open Questions

- Exact commercial Nominatim vendor for Expora prod (LocationIQ vs Geoapify geocode vs other) — ops choice; code only needs URL + optional key.
