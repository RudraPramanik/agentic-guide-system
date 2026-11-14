## 1. Agent checkpoint and architecture rollup

- [x] 1.1 In `docs/context.md`, replace the header next-step (“first VPS deploy”) and the deployment sentence (“Live API URL TBD after first VPS bring-up”) with the canonical hosts: site `https://explorai.online` and `https://www.explorai.online`, API `https://api.explorai.online`. Bump **Last updated**. Leave the progress table and the stub list unchanged. Do not claim `/api/v1/health` or Redis is healthy.
- [x] 1.2 In `docs/app/system.md`, replace the build-status rollup sentence that says the next step is the first VPS deploy with the same canonical hosts. Do not edit the architecture sections.

## 2. VPS hosting notes

- [x] 2.1 In the application-hosting section of `docs/vps.md` only, point the DNS example at `api.explorai.online` and rewrite the cross-origin cookie paragraph so `SameSite=None` applies only when the frontend is a different site. State that the live pair shares `explorai.online` and stays on Option A (`SameSite=Lax`). Keep the links to `docs/steps/blueprint_production.md` and `ops/`. Do not rewrite the terminal log above that section and do not add secrets.

## 3. Production env template

- [x] 3.1 In `.env.production.example`, set `WANDR_API_HOST=api.explorai.online`, `GOOGLE_REDIRECT_URI=https://api.explorai.online/api/v1/auth/callback`, `FRONTEND_URL=https://explorai.online`, and `CORS_ALLOWED_ORIGINS` to `https://explorai.online` and `https://www.explorai.online` with no trailing slashes. Do not add secrets. Do not edit `.env.production` or `src/config.py`.

## 4. Check

- [x] 4.1 Grep `docs/context.md`, `docs/app/system.md`, `docs/vps.md`, and `.env.production.example` for `exporaai`, `tripai-stagging`, `api.example.com`, and “Live API URL TBD”. The only allowed hit is none in those living files (historical OpenSpec may still contain the old names). Confirm `src/` and `.env.production` were not modified.
