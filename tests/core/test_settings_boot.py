"""Settings boot: catalog without LLM_API_KEY; other missing env stays loud."""

from __future__ import annotations

import pytest

from src.config import get_settings


def _set_minimal_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://wandr:wandr@localhost:5433/wandr",
    )
    monkeypatch.setenv(
        "NOMINATIM_USER_AGENT",
        "wandr-test/0.1 (test@example.com)",
    )


def test_get_settings_boots_without_llm_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    _set_minimal_required_env(monkeypatch)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.LLM_API_KEY == ""
    finally:
        get_settings.cache_clear()


def test_get_settings_missing_database_url_is_operator_readable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv(
        "NOMINATIM_USER_AGENT",
        "wandr-test/0.1 (test@example.com)",
    )
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL") as exc_info:
            get_settings()
        message = str(exc_info.value)
        assert ".env" in message
        assert "env_file" in message or "Compose" in message
    finally:
        get_settings.cache_clear()
