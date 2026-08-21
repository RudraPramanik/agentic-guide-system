"""Unit tests for chat_with_tools — mocked litellm only."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import litellm
import pytest

from src.core.exceptions import WandrLLMError
from src.core.llm.client import LLMToolResponse, chat_with_tools


def _completion_with_tool_call(
    name: str = "check_readiness",
    arguments: str = "{}",
) -> SimpleNamespace:
    fn = SimpleNamespace(name=name, arguments=arguments)
    tc = SimpleNamespace(function=fn)
    message = SimpleNamespace(tool_calls=[tc], content=None)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _completion_content_only(content: str = "hello") -> SimpleNamespace:
    message = SimpleNamespace(tool_calls=None, content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


@pytest.mark.asyncio
async def test_chat_with_tools_parses_tool_call() -> None:
    mock_resp = _completion_with_tool_call(
        name="rank_places",
        arguments='{"x": 1}',
    )
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_ac:
        result = await chat_with_tools(
            messages=[{"role": "user", "content": "plan"}],
            tools=[{"type": "function", "function": {"name": "rank_places"}}],
            tool_choice="auto",
        )

    assert isinstance(result, LLMToolResponse)
    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "rank_places"
    assert result.tool_calls[0]["arguments_json"] == '{"x": 1}'
    kwargs = mock_ac.await_args.kwargs
    assert kwargs["tools"]
    assert kwargs["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_chat_with_tools_content_only() -> None:
    mock_resp = _completion_content_only("no tools needed")
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await chat_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )

    assert result.tool_calls == []
    assert result.content == "no tools needed"


@pytest.mark.asyncio
async def test_chat_with_tools_exhausted_retries_raises_wandr_llm_error() -> None:
    with (
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.Timeout("timed out", model="x", llm_provider="y"),
        ),
        patch("src.core.llm.client.get_settings") as mock_settings,
    ):
        mock_settings.return_value = SimpleNamespace(
            LLM_MODEL="test-model",
            LLM_API_KEY="k",
            LLM_API_BASE="",
            LLM_TIMEOUT_SECONDS=1,
            LLM_MAX_RETRIES=2,
        )
        with pytest.raises(WandrLLMError) as exc_info:
            await chat_with_tools(
                messages=[{"role": "user", "content": "x"}],
                tools=[],
            )

    assert exc_info.value.code == "llm_unavailable"


@pytest.mark.asyncio
async def test_chat_with_tools_empty_api_key_raises_without_litellm() -> None:
    with (
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
        ) as mock_ac,
        patch("src.core.llm.client.get_settings") as mock_settings,
    ):
        mock_settings.return_value = SimpleNamespace(
            LLM_MODEL="test-model",
            LLM_API_KEY="   ",
            LLM_API_BASE="",
            LLM_TIMEOUT_SECONDS=1,
            LLM_MAX_RETRIES=2,
        )
        with pytest.raises(WandrLLMError) as exc_info:
            await chat_with_tools(
                messages=[{"role": "user", "content": "x"}],
                tools=[],
            )

    assert exc_info.value.code == "llm_unavailable"
    assert "LLM_API_KEY" in str(exc_info.value.message)
    assert ".env" in str(exc_info.value.message)
    mock_ac.assert_not_awaited()
