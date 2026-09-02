## 1. Config

- [x] 1.1 Add optional `NOMINATIM_API_KEY: str = ""` to `src/config.py` Settings
- [x] 1.2 Document `NOMINATIM_API_KEY`, real `NOMINATIM_USER_AGENT` guidance, and Nominatim URL override notes in `.env.example`

## 2. Geocoder gateway

- [x] 2.1 In `src/geo/geocoder.py`, on Nominatim HTTP 403/429 raise `ExternalServiceError(service="nominatim", ...)` instead of returning `None`; keep empty `200` / soft failures as `None`
- [x] 2.2 When `NOMINATIM_API_KEY` is non-empty, attach query param `key` on Nominatim search requests
- [x] 2.3 Ensure policy/rate `ExternalServiceError` paths do not write into the process geocode cache
- [x] 2.4 Add/adjust unit tests for 403→`ExternalServiceError`, empty→`None`, no negative-cache of 403, and API key param

## 3. Destinations search

- [x] 3.1 Update `DestinationService.search` so `ExternalServiceError` from geocode propagates (not mapped to `DestinationNotFoundError`); keep `None` → `DestinationNotFoundError`
- [x] 3.2 Add/adjust destination service (and HTTP if present) tests: upstream failure → 502 envelope / `external_service_error`; nonsense → 404 `not_found`

## 4. Overpass headers

- [x] 4.1 Send `Accept: application/json` with existing `User-Agent` from `NOMINATIM_USER_AGENT` in `_post_overpass`
- [x] 4.2 Adjust Overpass unit test(s) to assert `Accept` / `User-Agent` on the POST

## 5. Production docs / templates

- [x] 5.1 Update `.env.production.example`: remove `contact@example.com` UA; document real contact UA, `NOMINATIM_API_KEY`, Overpass/`PLACES_SOURCES` notes
- [x] 5.2 Update `docs/steps/blueprint_production.md` geo checklist: cloud-IP Nominatim warning, provider swap, Overpass fallbacks
- [x] 5.3 Update `docs/vps.md` with short geo troubleshooting (502 vs empty catalog)

## 6. Proof

- [x] 6.1 Run targeted pytest for geocoder + destinations + overpass changes
- [x] 6.2 Manual check: with mocked/forced 403 path, search returns 502 `external_service_error` not 404
