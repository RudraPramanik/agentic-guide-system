## 1. Settings boot

- [x] 1.1 In `src/config.py`, set `LLM_API_KEY: str = ""` and update the field comment: catalog/health boot without a key; generate/enrich need a real key via the LLM gateway.
- [x] 1.2 Update the `get_settings()` `RuntimeError` message so it no longer claims `LLM_API_KEY` is required for catalog routes; keep naming other missing required fields and Compose `.env` / `.env.example`.

## 2. LLM gateway guard

- [x] 2.1 In `src/core/llm/client.py`, add a shared empty-key check (strip) that raises `WandrLLMError(code="llm_unavailable")` naming `LLM_API_KEY` and `.env` before LiteLLM.
- [x] 2.2 Call that check from `chat_completion`, `chat_with_tools`, and `embed_texts` when the resolved key would be `LLM_API_KEY` (or empty after GEMINI fallback). Do not use `os.environ.get()`.

## 3. Tests

- [x] 3.1 Rewrite `tests/core/test_settings_boot.py`: without `LLM_API_KEY` but with other required env present, `get_settings()` succeeds and `LLM_API_KEY == ""`. Keep a test that missing `DATABASE_URL` still raises operator-readable `RuntimeError`. Always `cache_clear()` in `finally`.
- [x] 3.2 Add/extend an LLM unit test proving empty `LLM_API_KEY` raises `WandrLLMError` without calling `litellm.acompletion`.
- [x] 3.3 Run `python -m pytest tests/core/test_settings_boot.py tests/core/test_llm_chat_with_tools.py -v` (and any new empty-key test module).

## 4. Docs tracking

- [x] 4.1 Write `docs/issue_solve.md`: symptom (FE CONNECTION_REFUSED / no destination results), root cause (API exit on required LLM key), why prior fix was temporary, permanent fix (boot-optional key + gateway guard), proof commands, non-goals.
- [x] 4.2 Update `.env.example` comment: empty/commented `LLM_API_KEY` no longer blocks `:8000`; generate/enrich still need a real key.
- [x] 4.3 Update `docs/context.md`, `docs/FE_guide.md`, and `docs/app/system.md` local-boot notes to match the new contract.

## 5. Stop

- [x] 5.1 Do not change destinations/search, CORS, cookies, sibling frontend, Compose service topology, or parent tripplanner OpenSpec. Do not commit `.env`.
