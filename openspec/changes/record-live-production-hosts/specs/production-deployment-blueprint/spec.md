## ADDED Requirements

### Requirement: Living deploy docs name the canonical public hosts
After the public site and API hostname are in DNS, `docs/context.md`, `docs/app/system.md`, and `docs/vps.md` MUST name the canonical hosts: site `https://explorai.online` (and `www.explorai.online`), API `https://api.explorai.online`. Those pages MUST NOT describe first VPS bring-up as still pending, MUST NOT say the live API URL is TBD, and MUST NOT cite `exporaai.xyz` or `tripai-stagging.vercel.app` as a current origin. `docs/vps.md` MUST still point at `docs/steps/blueprint_production.md` and `ops/` and MUST NOT embed secrets. The SameSite=None note MUST apply only when the frontend origin is a different site; the live pair shares the registrable domain `explorai.online` and stays on the locked Option A (`SameSite=Lax`). These pages MUST NOT state that `/api/v1/health` or Redis is healthy; operators still confirm liveness with `ops/health.sh`.

#### Scenario: Agent checkpoint no longer waits on first deploy
- **WHEN** a reader opens the phase line and the deployment note in `docs/context.md`
- **THEN** they see the canonical site and API hosts and do not see “first VPS deploy” or “Live API URL TBD” as the next step

#### Scenario: Architecture rollup matches the checkpoint
- **WHEN** a reader opens the build-status rollup in `docs/app/system.md`
- **THEN** it names the same canonical hosts and does not say the next step is the first VPS deploy

#### Scenario: VPS notes use the live pair
- **WHEN** a reader opens the application-hosting section of `docs/vps.md`
- **THEN** the example origins are `explorai.online` / `api.explorai.online`, SameSite=None is not required for that pair, and the blueprint plus `ops/` links remain

### Requirement: Production env template uses the canonical public origins
`.env.production.example` MUST set `WANDR_API_HOST` to `api.explorai.online`, `GOOGLE_REDIRECT_URI` to `https://api.explorai.online/api/v1/auth/callback`, `FRONTEND_URL` to `https://explorai.online`, and `CORS_ALLOWED_ORIGINS` to `https://explorai.online` and `https://www.explorai.online` with no trailing slashes. It MUST NOT list `tripai-stagging.vercel.app` or `api.example.com` as those values. The file MUST remain free of secrets. Existing field-name and scheme rules for database, Redis, Qdrant, and embeddings are unchanged.

#### Scenario: Operator copies the template
- **WHEN** an operator reads the public-origin fields in `.env.production.example`
- **THEN** they see the canonical API host, OAuth callback, frontend origin, and both site origins, and they do not see the retired Vercel preview origin
