## Context

See proposal.md — Why. Living pages still say first deploy is next and still name `api.exporaai.xyz` and `https://tripai-stagging.vercel.app`. Checked 2026-11-14: `explorai.online` returns HTTP 200, `www.explorai.online` is a Vercel CNAME, `api.explorai.online` resolves through Cloudflare, and `exporaai.xyz` / `api.exporaai.xyz` are NXDOMAIN. `/api/v1/health` returned 503 and then timed out on the body, so this change records names, not a green bill of health.

## Goals / Non-Goals

**Goals:**

- One canonical pair written the same way in the agent checkpoint, the architecture rollup, the VPS hosting notes, and the committed env template.
- Cookie guidance that matches the locked Option A note: same registrable domain, `SameSite=Lax`. `SameSite=None` stays documented only for a frontend on a different site.

**Non-Goals:**

- Runtime defaults in `src/config.py`, the filled `.env.production`, cookie or CORS code, ops scripts, Docker, archived OpenSpec, and `openspec/changes/cross-site-prod-auth-cookies`.
- Rewriting the terminal log that makes up the top of `docs/vps.md`.
- Parent vault or frontend guides (they use placeholders).
- A dated “API is up” or “Redis is up” sentence. `/health` does not check Redis.

## Decisions

### Write the live hosts into the template, not `api.example.com`

The template is what operators copy. `api.example.com` and the retired Vercel preview are how the stale origin survived. `WANDR_API_HOST=api.explorai.online`, callback `https://api.explorai.online/api/v1/auth/callback`, `FRONTEND_URL=https://explorai.online`, CORS for both `https://explorai.online` and `https://www.explorai.online`.

Alternative: leave placeholders and only fix prose. Rejected — the example file is the copy source, and it is the only committed file that still names `tripai-stagging.vercel.app` outside historical OpenSpec.

### Touch the rollup lines, not the progress table

`docs/context.md` changes are the header date/next-step line and the deployment sentence that says the live API URL is TBD. `docs/app/system.md` changes are the one-line build-status rollup. The step table and stub list stay. `docs/vps.md` changes are the application-hosting section only (DNS row example plus the cross-origin cookie paragraph).

Alternative: rewrite `vps.md` into a clean SOP. Rejected — the blueprint is already the SOP; this file is a baseline log plus a short hosting pointer.

### Leave the code default alone

`src/config.py` still defaults `CORS_ALLOWED_ORIGINS` to the retired Vercel origin. Production is expected to override that from `.env.production`. Changing the default is a behavior change and is out of scope. The design records the drift so a later change can pick it up.

## Risks / Trade-offs

- [Health is not green on the day of writing] → Docs name hosts and keep `ops/health.sh` as the check. They do not say the API is up.
- [`src/config.py` default stays on the dead origin] → Called out above. A fresh process without `CORS_ALLOWED_ORIGINS` in the environment would still allow only the retired preview. Production override is the mitigation until a code change.
- [www vs apex] → Both are in the template CORS list because both names resolve to the site. If Vercel later redirects www away, the extra origin is harmless.
- [Historical OpenSpec still names the old pair] → Left as history so the cross-site cookie change still explains why `SameSite=None` was required then.

## Migration Plan

Docs and the example template only. No deploy, no image rebuild, no env push. Rollback is reverting those files. Operators who already copied `.env.production` are unaffected; the example does not overwrite the server file.

## Open Questions

None. Host names, file list, and the decision to leave `src/config.py` unchanged are fixed above.
