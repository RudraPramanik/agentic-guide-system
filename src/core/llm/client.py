"""Wandr — LiteLLM gateway. The only module that imports litellm."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import litellm
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    wait_exponential,
)

from src.config import get_settings
from src.core.exceptions import WandrLLMError
from src.core.observability.logging import get_logger

log = get_logger()


def _llm_stop(retry_state: RetryCallState) -> bool:
    return retry_state.attempt_number >= get_settings().LLM_MAX_RETRIES


def _log_llm_retry(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    model = retry_state.kwargs.get("model")
    if model is None:
        model = get_settings().LLM_MODEL
    wait_seconds = (
        retry_state.next_action.sleep
        if retry_state.next_action is not None
        else 0
    )
    log.warning(
        "llm_retry",
        model=model,
        attempt_number=retry_state.attempt_number,
        error_type=type(exc).__name__ if exc else "unknown",
        wait_seconds=wait_seconds,
    )


def _llm_retry_error(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception()
    raise WandrLLMError(
        code="llm_unavailable",
        message=f"LLM call failed after retries: {type(exc).__name__}",
    ) from exc


_llm_retry = retry(
    stop=_llm_stop,
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((litellm.Timeout, litellm.RateLimitError)),
    reraise=False,
    before_sleep=_log_llm_retry,
    retry_error_callback=_llm_retry_error,
)


@dataclass
class LLMToolResponse:
    tool_calls: list[dict]
    content: str | None


@_llm_retry
async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    response_format: dict | None = None,
) -> str:
    try:
        settings = get_settings()
        response = await litellm.acompletion(
            model=model or settings.LLM_MODEL,
            messages=messages,
            response_format=response_format,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content
    except litellm.RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except litellm.Timeout:
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e


@_llm_retry
async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_choice: str = "auto",
    model: str | None = None,
) -> LLMToolResponse:
    try:
        settings = get_settings()
        response = await litellm.acompletion(
            model=model or settings.LLM_MODEL,
            messages=messages,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            tools=tools,
            tool_choice=tool_choice,
        )
        message = response.choices[0].message
        raw_tool_calls = getattr(message, "tool_calls", None) or []
        if raw_tool_calls:
            tool_calls = [
                {
                    "name": tc.function.name,
                    "arguments_json": tc.function.arguments,
                }
                for tc in raw_tool_calls
            ]
            return LLMToolResponse(tool_calls=tool_calls, content=None)
        return LLMToolResponse(tool_calls=[], content=message.content)
    except litellm.RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except litellm.Timeout:
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e
