## Context

See `proposal.md` for why. Prior change `fix-api-boot-missing-llm-env` wrapped `get_settings()` ValidationError into an operator-readable `RuntimeError` and documented FE `:8000` refusal → `wandr_api` exited. It deliberately kept `LLM_API_KEY: str` required, so a gitignored/commented key still kills bind. Recurrence after `docker compose up` confirms that approach is messaging-only.

Compose `api` still runs `alembic upgrade head` then uvicorn; both call `get_settings()`. Catalog routes never import the LLM gateway. Generate/enrich already surface `WandrLLMError` through existing fail-soft paths.

## Goals / Non-Goals

**Goals:**

- Bind `:8000` without a real LLM secret so destinations search works after Compose up.
- Keep a single settings load path and a single LLM gateway (AGENT.md).
- Fail loudly at the gateway when generate/enrich runs without a key.
- Document the incident and permanent fix in `docs/issue_solve.md`.

**Non-Goals:**

- Placeholder secrets in `docker-compose.yml`.
- New env names, endpoints, packages, or FE changes.
- Making `SECRET_KEY` / `DATABASE_URL` / `NOMINATIM_USER_AGENT` optional.
- Changing destinations/search behavior beyond “API is listening.”

## Decisions

### 1. Default `LLM_API_KEY` to empty string

**Choice:** `LLM_API_KEY: str = ""` in Settings (same pattern as `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`). Missing/commented env no longer raises Pydantic `missing`.

**Why:** Permanent — does not depend on an uncommitted secret being present for catalog boot.

**Alternative considered:** Keep required key + clearer error (status quo). Rejected — recurrence after Compose up.

**Alternative considered:** Inject `LLM_API_KEY=change-me` only in Compose `environment:`. Rejected — host uvicorn/Alembic still break; invents stack-only coupling.

### 2. Empty-key guard only in `src/core/llm/client.py`

**Choice:** Shared helper checked at the start of `chat_completion`, `chat_with_tools`, and `embed_texts` (when that path uses `LLM_API_KEY`). Raise `WandrLLMError(code="llm_unavailable", …)` naming `LLM_API_KEY` and `.env` before LiteLLM. No `os.environ.get()`.

**Why:** AGENT.md — sole LLM module. Planner nodes already catch/fail-soft on gateway errors for prefs/narrative; generate remains misconfig-loud without taking down the process.

**Alternative considered:** Midware “LLM readiness” endpoint. Rejected — invents surface; out of scope.

### 3. Keep ValidationError wrap for other required fields

**Choice:** Retain `get_settings()` catch of Pydantic `missing` → `RuntimeError`, but drop copy that says `LLM_API_KEY` is required for catalog routes.

**Why:** Operators still need readable failures for `DATABASE_URL` / `SECRET_KEY` / `NOMINATIM_USER_AGENT`.

### 4. Docs + issue tracking

**Choice:** Update FE_guide / context / system / `.env.example`, and write `docs/issue_solve.md` with symptom → root cause → temporary fix → permanent fix → proof.

**Why:** User asked for durable tracking; prior fix was easy to re-misdiagnose as a FE network bug.

## Risks / Trade-offs

- [Developers boot without a key and only discover it at generate] → Mitigation: gateway error names `LLM_API_KEY` / `.env`; docs state catalog vs generate clearly.
- [Whitespace-only key treated as set] → Mitigation: strip before the empty check.
- [Hosted embeddings path using `LLM_API_KEY` as fallback] → Mitigation: same empty-key guard on `embed_texts` when that key would be used; local MiniLM backend unchanged.
- [Prior OpenSpec said key must stay required] → Mitigation: this change supersedes that requirement explicitly in delta specs.

## Migration Plan

No DB migration. Pull code → `docker compose up --build`. Catalog works without restoring a key; set a real `LLM_API_KEY` only when testing generate/enrich. Rollback: revert Settings default and gateway guard; restore old boot message.

## Open Questions

None.
