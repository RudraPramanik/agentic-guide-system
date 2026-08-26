"""Pinned tests for LLMUsage capture and retry bookkeeping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import litellm
import pytest

from src.core.exceptions import WandrLLMError
from src.core.llm.client import (
    ChatCompletionResult,
    LLMToolResponse,
    LLMUsage,
    chat_completion,
    chat_with_tools,
    embed_texts,
    merge_token_usage,
)


def _usage(prompt: int = 3, completion: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
    )


def _completion_content(
    content: str = '{"ok": true}',
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    message = SimpleNamespace(tool_calls=None, content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


def _completion_with_tool(
    name: str = "check_readiness",
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    fn = SimpleNamespace(name=name, arguments="{}")
    tc = SimpleNamespace(function=fn)
    message = SimpleNamespace(tool_calls=[tc], content=None)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_chat_completion_captures_usage() -> None:
    mock_resp = _completion_content(usage=_usage(10, 20))
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            response_format={"type": "json_object"},
        )
    assert isinstance(result, ChatCompletionResult)
    assert result.content == '{"ok": true}'
    assert result.usage == LLMUsage(10, 20, 30)
    assert result.retry_count == 0


@pytest.mark.asyncio
async def test_chat_completion_empty_usage_degrades() -> None:
    mock_resp = _completion_content(usage=None)
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await chat_completion(messages=[{"role": "user", "content": "hi"}])
    assert result.usage == LLMUsage()
    assert result.content == '{"ok": true}'


@pytest.mark.asyncio
async def test_chat_with_tools_captures_usage() -> None:
    mock_resp = _completion_with_tool(usage=_usage(1, 2))
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await chat_with_tools(
            messages=[{"role": "user", "content": "plan"}],
            tools=[{"type": "function", "function": {"name": "check_readiness"}}],
        )
    assert isinstance(result, LLMToolResponse)
    assert result.usage == LLMUsage(1, 2, 3)
    assert len(result.tool_calls) == 1


@pytest.mark.asyncio
async def test_embed_texts_return_contract_unchanged() -> None:
    row = SimpleNamespace(index=0, embedding=[0.1, 0.2])
    mock_resp = SimpleNamespace(data=[row], usage=_usage(4, 0))
    with patch(
        "src.core.llm.client.litellm.aembedding",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        vectors = await embed_texts(["hello"])
    assert vectors == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_chat_with_tools_counts_retries() -> None:
    ok = _completion_with_tool(usage=_usage(1, 1))
    timeout = litellm.Timeout("t", model="m", llm_provider="test")
    with patch(
        "src.core.llm.client.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[timeout, ok],
    ):
        with patch("src.core.llm.client.asyncio.sleep", new_callable=AsyncMock):
            result = await chat_with_tools(
                messages=[{"role": "user", "content": "x"}],
                tools=[],
            )
    assert result.retry_count == 1


def test_merge_token_usage_sums() -> None:
    merged = merge_token_usage(
        {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        LLMUsage(4, 5, 9),
    )
    assert merged == {
        "prompt_tokens": 5,
        "completion_tokens": 7,
        "total_tokens": 12,
    }


@pytest.mark.asyncio
async def test_chat_with_tools_empty_api_key_still_raises() -> None:
    with patch("src.core.llm.client.get_settings") as gs:
        gs.return_value = SimpleNamespace(
            LLM_API_KEY="",
            LLM_MODEL="m",
            LLM_API_BASE="",
            LLM_TIMEOUT_SECONDS=5,
            LLM_MAX_RETRIES=2,
        )
        with pytest.raises(WandrLLMError):
            await chat_with_tools(messages=[], tools=[])
