## Context

See proposal.md — Why. `docker-compose.yml` maps `8001:8000`. Uvicorn and the in-container healthcheck stay on port 8000. `docs/app/system.md` and `docs/context.md` still describe host port 8000, and so does the current `local-docker-dev-stack` requirement.

## Goals / Non-Goals

**Goals:**

- One sentence a reader can trust: from the host, Compose API is `http://localhost:8001`; inside the container it is port 8000.
- The quick-ref clash note names the port Compose actually publishes.

**Non-Goals:**

- Editing `docker-compose.yml`, Dockerfiles, or run scripts. The mapping is already `8001:8000`.
- Moving optional host uvicorn off port 8000. That process runs only when the Compose API service is stopped.
- `docs/FE_guide.md`, `docs/issue_solve.md`, `docs/steps/step*.md`, `docs/blueprint_frontend.md`, frontend env, and CORS.

## Decisions

### Document the published port; do not move it back to 8000

The compose file is the running contract. Restoring a `8000:8000` publish would collide with whatever led to the alternate port and would be a behavior change. Docs and the spec move to 8001.

Alternative: change Compose back to 8000 so the old spec stays true. Rejected — this change does not touch the stack.

### Rewrite the quick-ref clash lines, not only the URL comment

`docs/context.md` says to stop anything on `:8000` before `docker compose up`, and that `docker compose down` unbinds `:8000`. After the publish move, the clash port is 8001. Leaving those bullets next to a corrected URL would still send someone to the wrong port. The optional host-uvicorn example in that section keeps `--port 8000`.

### Leave `docs/FE_guide.md` for a follow-up

That guide still says the Compose API and `NEXT_PUBLIC_API_URL` are `http://localhost:8000`. It is a living contract, and it will disagree with this change until a later edit. Folding it in would also pull the sibling frontend default into this backend docs pass. Called out so apply does not “fix” it in passing.

## Risks / Trade-offs

- [`docs/FE_guide.md` still says `:8000`] → Agents who open that guide instead of `context.md` still get the old URL. Follow-up, not this change.
- [Historical step logs and `issue_solve.md` still say `:8000`] → Left as the record of the port those incidents used. They are not the session checkpoint.
- [Spec and compose could drift again] → The new requirement names both ports. A verify task checks the compose mapping is still `8001:8000` and that the two living sections no longer claim Compose publishes 8000.

## Migration Plan

Docs and the delta spec only. No image rebuild and no env push. Rollback is reverting those doc lines. Compose is untouched, so rollback does not move the port.

## Open Questions

None. Host port 8001, container port 8000, and the file list are fixed above.
