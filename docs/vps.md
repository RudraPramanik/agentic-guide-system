# VPS baseline

Baseline is done: about 1 GB RAM, 2 GB swap, amd64. UFW allows inbound 22, 80, and 443. Repeatable hosting is in the sections below, `docs/steps/blueprint_production.md`, and `ops/`.

## Application hosting

VPS baseline is complete (swap, UFW, amd64). Public hosts are in DNS: site `https://explorai.online` and `https://www.explorai.online`; API `https://api.explorai.online`. The table below is the repeatable hosting SOP: `docs/steps/blueprint_production.md` and `ops/`.

| Step | Command / action |
|------|------------------|
| OCI Security List | Allow inbound **22, 80, 443** (in addition to UFW) |
| Install Docker | `sudo apt install -y docker.io docker-compose-v2` |
| Clone repo | `git clone … ~/guideagent && cd ~/guideagent` |
| Env | `cp .env.production.example .env.production` → fill hosted URLs/keys |
| DNS | `WANDR_API_HOST=api.explorai.online` → VPS public IP |
| Migrate | `./ops/migrate.sh` |
| Reindex | If 384→768 cutover: `docker run --rm --env-file .env.production $IMAGE python scripts/index_places.py …` |
| Deploy | `./ops/deploy.sh` or `./ops/deploy.sh <git-sha>` after GHCR push |
| Smoke | `./ops/health.sh` then planner SSE (§7 in blueprint) |

**CI/CD:** GitHub Actions `deploy` workflow (`workflow_dispatch`) — set secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optional `VPS_APP_DIR`. VPS must `docker login ghcr.io` once.

**Do not** `docker build` on the 1GB VPS — pull from GHCR or transfer a prebuilt image.

**Live origins** share the registrable domain `explorai.online` (site `https://explorai.online` / `https://www.explorai.online`, API `https://api.explorai.online`), so auth cookies stay Option A (`SameSite=Lax`). **Frontend on a different site:** production cookies must be `SameSite=None; Secure` (see blueprint §6). Env-only restarts are not enough for that cookie change — ship a new API image, then clear browser cookies.

---

## Geo upstream troubleshooting

Destination search and prepare depend on external geo APIs. Auth/Redis/Qdrant healthy does **not** mean search works.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `GET /api/v1/destinations/search?q=London` → **502** `external_service_error` (service=`nominatim`) | Public Nominatim blocked UA or cloud IP | Set real `NOMINATIM_USER_AGENT` (email); if still 403, set `NOMINATIM_BASE_URL` + `NOMINATIM_API_KEY` to a Nominatim-compatible free tier |
| Search → **404** `not_found` | True miss or geocode timeout | Try a known city; check `SEARCH_GEOCODE_TIMEOUT_SECONDS` |
| Search 200 but prepare/places empty | Overpass 4xx from VPS | Set free `OPENTRIPMAP_API_KEY` / `GEOAPIFY_API_KEY`; prefer `PLACES_SOURCES=opentripmap,geoapify` |

Probe from the API container (after env change, restart API so process geocode cache clears):

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api \
  python -c 'import httpx,os; u=os.environ["NOMINATIM_BASE_URL"]+"/search"; r=httpx.get(u,params={"q":"London","format":"json","limit":1},headers={"User-Agent":os.environ["NOMINATIM_USER_AGENT"]},timeout=10); print(r.status_code); print(r.text[:300])'
```
