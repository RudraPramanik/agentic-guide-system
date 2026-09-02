## MODIFIED Requirements

### Requirement: Env and API checklist is explicit
The production blueprint MUST list every external account/API to provision and every application env var required for first boot (database, Qdrant, Redis, LLM, Gemini embeddings, Google OAuth, CORS, secrets, geo user-agent), including which values are prod-only vs optional. The geo section MUST require a real contact string in `NOMINATIM_USER_AGENT` (MUST NOT recommend `contact@example.com`), MUST warn that public `nominatim.openstreetmap.org` often returns 403 from cloud/VPS IPs, MUST document optional `NOMINATIM_API_KEY` plus `NOMINATIM_BASE_URL` override for Nominatim-compatible providers, and MUST note Overpass public-mirror 4xx risk with `OVERPASS_API_URL` / `PLACES_SOURCES` fallbacks (opentripmap, geoapify).

#### Scenario: Checklist covers embeddings and OAuth redirect
- **WHEN** an operator follows the checklist section
- **THEN** they see `PLACES_EMBEDDING_BACKEND`/`MODEL`/`DIM`, Gemini API key handling, and `GOOGLE_REDIRECT_URI` pointing at the HTTPS API callback path

#### Scenario: Checklist covers prod geocoder policy
- **WHEN** an operator follows the geo checklist
- **THEN** they see a real User-Agent requirement, public-OSM cloud-IP warning, and guidance to set `NOMINATIM_BASE_URL` / `NOMINATIM_API_KEY` when public Nominatim is blocked

### Requirement: Committed production env template uses Settings field names
The project SHALL provide `.env.production.example` (committed, no secrets) listing every production env var required for first boot with names matching `src/config.py` Settings. The template MUST document: `PLACES_EMBEDDING_BACKEND=hosted`, `PLACES_EMBEDDING_MODEL`, `PLACES_EMBEDDING_DIM=768`, `REDIS_URL` as `redis://` or `rediss://` (not HTTPS REST), `DATABASE_URL` as `postgresql+asyncpg://`, hosted `QDRANT_URL`, production OAuth redirect HTTPS path, and `CORS_ALLOWED_ORIGINS` without trailing slashes on origins. For geo, the template MUST use a clearly fake-but-non-placeholder pattern that tells operators to substitute a real email (not `contact@example.com`), MUST document `NOMINATIM_API_KEY` (empty by default), and MUST comment Overpass/`PLACES_SOURCES` prod notes.

#### Scenario: Operator copies template to server
- **WHEN** an operator copies `.env.production.example` to `.env.production` on the VPS and fills secrets
- **THEN** no ignored env aliases (e.g. `EMBEDDING_MODEL`, `UPSTASH_REDIS_REST_TOKEN`) are required for the app to boot

#### Scenario: Template does not ship example.com as the prod User-Agent
- **WHEN** an operator reads `.env.production.example` geo lines
- **THEN** they are instructed to set a real contact email and see `NOMINATIM_API_KEY` documented

### Requirement: VPS operator notes link blueprint and ops
`docs/vps.md` MUST summarize VPS baseline steps already completed and point to `docs/steps/blueprint_production.md` and `ops/` for application hosting (without embedding live secrets). It MUST include a short geo-upstream troubleshooting note: search 502/`external_service_error` means Nominatim blocked; fix User-Agent or swap `NOMINATIM_BASE_URL` (+ key); empty places after search works → check Overpass/`PLACES_SOURCES`.

#### Scenario: Agent reads vps.md for deploy context
- **WHEN** a developer or Cursor agent opens `docs/vps.md`
- **THEN** they see next application-hosting steps and links to ops scripts

#### Scenario: Operator debugs destination search on VPS
- **WHEN** an operator opens the geo troubleshooting note in `docs/vps.md`
- **THEN** they can distinguish Nominatim block (502) from empty catalog and know which env knobs to change
