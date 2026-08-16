## Why

Guests can finish `POST /planner/generate` and then get HTTP 403 on `GET /trips/{id}` with “This trip belongs to a different session.” Auth is optional on that GET; login does not help. The ownership check is correct (`wandr_session` must equal `Trip.session_id`). The usual local cause is mixing `localhost` and `127.0.0.1`: they are different cookie jars under `SameSite=Lax`. Sibling FE already hints when hosts differ. Default `CORS_ALLOWED_ORIGINS` only lists `http://localhost:3000`, so operators who follow the 127.0.0.1 API URL cannot open the app at `http://127.0.0.1:3000` and fall back to `localhost:3000`, which splits cookies.

## What Changes

- Default `CORS_ALLOWED_ORIGINS` includes both local Next origins: `http://localhost:3000` and `http://127.0.0.1:3000`.
- Document in `.env.example` and `docs/FE_guide.md` that the **page hostname must match** `NEXT_PUBLIC_API_URL`’s hostname. Listing both CORS origins does **not** merge cookie jars.
- CORS tests cover the 127.0.0.1 origin the same way as localhost.
- **Non-goals:** Do not change `TripService.assert_can_access`, cookie `SameSite`/`httpOnly`/`secure`, planner generate session minting, or sibling frontend code. Do not add `*` to CORS. Do not invent a session-mismatch API error code.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `cors-middleware`: Default credentialed origins MUST include both `http://localhost:3000` and `http://127.0.0.1:3000`. Wildcard-with-credentials remains forbidden. Cookie SameSite policy stays Lax (Option A).

## Impact

- `src/config.py` default `CORS_ALLOWED_ORIGINS`
- `.env.example` CORS example list
- `tests/core/test_cors_middleware.py`
- `docs/FE_guide.md` (local host pairing; CORS must list the origin actually used)
- No new packages, endpoints, env var names, or cookie flags
- Operators still must pick one pair: `localhost:3000`+`localhost:8000` **or** `127.0.0.1:3000`+`127.0.0.1:8000`. Mixed hosts remain 403 by design.
