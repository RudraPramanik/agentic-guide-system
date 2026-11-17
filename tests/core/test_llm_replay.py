"""Gateway record/replay. No live provider calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings
from src.core.exceptions import WandrLLMError
from src.core.llm.client import (
    chat_completion,
    chat_with_tools,
    embed_texts,
    replay_misses,
    use_llm_replay,
)


def _content_response(content: str = "hello") -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(
        choices=[choice],
        usage={"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    )


def _tool_response(name: str, arguments: str) -> SimpleNamespace:
    fn = SimpleNamespace(name=name, arguments=arguments)
    tc = SimpleNamespace(function=fn)
    message = SimpleNamespace(tool_calls=[tc], content=None)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(
        choices=[choice],
        usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    )


def _embed_response(vectors: list[list[float]]) -> SimpleNamespace:
    data = [
        {"index": index, "embedding": row} for index, row in enumerate(vectors)
    ]
    return SimpleNamespace(data=data, usage={"prompt_tokens": 4, "total_tokens": 4})


def test_replay_mode_defaults_off() -> None:
    assert get_settings().LLM_REPLAY_MODE == "off"


def test_replay_mode_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_REPLAY_MODE", "live")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_off_mode_calls_provider(tmp_path) -> None:
    mock_resp = _content_response("from-provider")
    with (
        use_llm_replay("off", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_ac,
    ):
        result = await chat_completion(messages=[{"role": "user", "content": "hi"}])
    assert result.content == "from-provider"
    assert mock_ac.await_count == 1


@pytest.mark.asyncio
async def test_replay_twice_matches_and_skips_provider(tmp_path) -> None:
    mock_resp = _content_response("recorded")
    messages = [{"role": "user", "content": "plan darjeeling"}]
    with (
        use_llm_replay("record", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_ac,
    ):
        recorded = await chat_completion(messages=messages)
    assert mock_ac.await_count == 1
    assert recorded.content == "recorded"

    with (
        use_llm_replay("replay", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=AssertionError("provider called"),
        ),
    ):
        first = await chat_completion(messages=messages)
        second = await chat_completion(messages=messages)
    assert first.content == second.content == "recorded"
    assert first.usage.total_tokens == second.usage.total_tokens == 8


@pytest.mark.asyncio
async def test_replay_tool_fixture_keeps_name_and_arguments(tmp_path) -> None:
    mock_resp = _tool_response("rank_places", '{"limit": 3}')
    messages = [{"role": "user", "content": "tools"}]
    tools = [{"type": "function", "function": {"name": "rank_places"}}]
    with (
        use_llm_replay("record", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        await chat_with_tools(messages, tools, tool_choice="auto")

    with (
        use_llm_replay("replay", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=AssertionError("provider called"),
        ),
    ):
        result = await chat_with_tools(messages, tools, tool_choice="auto")
    assert result.tool_calls == [
        {"name": "rank_places", "arguments_json": '{"limit": 3}'}
    ]


@pytest.mark.asyncio
async def test_trace_duration_does_not_change_fixture(tmp_path) -> None:
    mock_resp = _tool_response("check_readiness", "{}")
    tools = [{"type": "function", "function": {"name": "check_readiness"}}]
    recorded = [{"role": "system", "content": "Recent tool_trace:\n- search ok=True code=None ms=18.4"}]
    replayed = [{"role": "system", "content": "Recent tool_trace:\n- search ok=True code=None ms=240.1"}]
    with (
        use_llm_replay("record", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        await chat_with_tools(recorded, tools, tool_choice="auto")

    with (
        use_llm_replay("replay", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=AssertionError("provider called"),
        ),
    ):
        result = await chat_with_tools(replayed, tools, tool_choice="auto")
    assert result.tool_calls[0]["name"] == "check_readiness"


@pytest.mark.asyncio
async def test_replay_embedding_fixture_keeps_vectors(tmp_path) -> None:
    vectors = [[0.25, 0.5], [0.75, 1.0]]
    texts = ["tea", "ridge"]
    with (
        use_llm_replay("record", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.aembedding",
            new_callable=AsyncMock,
            return_value=_embed_response(vectors),
        ) as mock_embed,
    ):
        recorded = await embed_texts(texts)
    assert mock_embed.await_count == 1
    assert recorded == vectors

    with (
        use_llm_replay("replay", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.aembedding",
            new_callable=AsyncMock,
            side_effect=AssertionError("provider called"),
        ),
    ):
        replayed = await embed_texts(texts)
    assert replayed == vectors


@pytest.mark.asyncio
async def test_missing_fixture_raises_replay_miss(tmp_path) -> None:
    with (
        use_llm_replay("replay", root=tmp_path),
        patch(
            "src.core.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=AssertionError("provider called"),
        ),
    ):
        with pytest.raises(WandrLLMError) as caught:
            await chat_completion(messages=[{"role": "user", "content": "missing"}])
        assert caught.value.code == "replay_miss"
        assert "replay_miss" in caught.value.message
        assert replay_misses()
        assert replay_misses()[0] in caught.value.message
