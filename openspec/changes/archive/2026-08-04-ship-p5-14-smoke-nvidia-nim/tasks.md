## 1. Provider env (local + example)

- [x] 1.1 Remap local `.env` canonical trio to NVIDIA NIM: `LLM_MODEL=nvidia_nim/meta/llama-3.1-8b-instruct` (or another free `nvidia_nim/...` if needed), `LLM_API_KEY` = NIM key, `LLM_API_BASE=https://integrate.api.nvidia.com/v1`; comment Gemini (or other) as flip-back — never commit `.env`
- [x] 1.2 Update `.env.example` with NIM `LLM_API_BASE` example plus commented alternate provider examples (Gemini/Groq/OpenAI-style); placeholder keys only; state that swap is env-only
- [x] 1.3 Verify `get_settings().LLM_MODEL` starts with `nvidia_nim/` via project venv + `PYTHONPATH`
- [x] 1.4 Confirm no new provider-specific branches landed under `src/planner/` or `src/travel_engine/` (gateway-only litellm import still holds)

## 2. Preconditions

- [x] 2.1 Ensure Docker Postgres (:5433) + Qdrant (:6335) are up
- [x] 2.2 Confirm Darjeeling exists seeded+enriched+indexed (or fail loud before blaming LLM)

## 3. Smoke + pytest

- [x] 3.1 Run `python scripts/test_agent.py` (venv + `PYTHONPATH`); on failure try alternate free `nvidia_nim/...` model before declaring blocked
- [x] 3.2 Run `python -m pytest tests/ -q` and confirm green
- [x] 3.3 Run step5.14 import guards (`litellm` only in `core/llm/client.py`; `travel_engine` purity)

## 4. Context ship

- [x] 4.1 Update `docs/context.md`: Last updated; Progress 5.1–5.14 ✅; Next step → P6.1; PlannerService real; keep trips CRUD / planner HTTP as P6 stubs; do not register `/planner/generate`; do not claim NIM-only product lock-in
- [x] 4.2 Confirm no FastAPI route contains `planner/generate`
