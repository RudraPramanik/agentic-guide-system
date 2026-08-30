"""Wandr — LiteLLM gateway. The only module that imports litellm."""

from __future__ import annotations

import asyncio
import contextvars
import time
from dataclasses import dataclass, field
from typing import Any

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

# Retries observed for the in-flight gateway call (before_sleep bumps).
_retry_bumps: contextvars.ContextVar[int] = contextvars.ContextVar(
    "llm_retry_bumps", default=0
)


@dataclass(frozen=True)
class LLMUsage:
    """Token counts from a provider response; empty when usage is absent."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatCompletionResult:
    """chat_completion return — content plus captured usage/retries."""

    content: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    retry_count: int = 0


def _embedding_api_key(settings) -> str:
    """Prefer GEMINI_API_KEY for gemini/* embed models; else LLM_API_KEY."""
    model = settings.PLACES_EMBEDDING_MODEL
    if model.startswith("gemini/") and settings.GEMINI_API_KEY:
        return settings.GEMINI_API_KEY
    if settings.GEMINI_API_KEY:
        return settings.GEMINI_API_KEY
    return settings.LLM_API_KEY


def _require_llm_api_key(settings) -> str:
    """Refuse empty LLM_API_KEY before LiteLLM (catalog boot stays key-optional)."""
    key = (settings.LLM_API_KEY or "").strip()
    if not key:
        raise WandrLLMError(
            code="llm_unavailable",
            message=(
                "LLM_API_KEY is empty. Set it in the Compose env_file `.env` "
                "(see `.env.example`) before generate/enrich."
            ),
        )
    return key


def _require_embedding_api_key(settings) -> str:
    """Refuse empty resolved embedding key before LiteLLM."""
    key = (_embedding_api_key(settings) or "").strip()
    if not key:
        raise WandrLLMError(
            code="llm_unavailable",
            message=(
                "Embedding API key is empty. Set LLM_API_KEY (or GEMINI_API_KEY "
                "for gemini/* embeddings) in the Compose env_file `.env` "
                "(see `.env.example`)."
            ),
        )
    return key


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


def _before_sleep_llm(retry_state: RetryCallState) -> None:
    _retry_bumps.set(_retry_bumps.get() + 1)
    _log_llm_retry(retry_state)


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
    before_sleep=_before_sleep_llm,
    retry_error_callback=_llm_retry_error,
)


def _usage_from_response(response: object) -> LLMUsage:
    """Extract usage; missing/partial → empty/zeros, never raise."""
    try:
        raw = getattr(response, "usage", None)
        if raw is None and isinstance(response, dict):
            raw = response.get("usage")
        if raw is None:
            return LLMUsage()
        if isinstance(raw, dict):
            prompt = int(raw.get("prompt_tokens") or 0)
            completion = int(raw.get("completion_tokens") or 0)
            total = int(raw.get("total_tokens") or (prompt + completion))
        else:
            prompt = int(getattr(raw, "prompt_tokens", 0) or 0)
            completion = int(getattr(raw, "completion_tokens", 0) or 0)
            total = int(getattr(raw, "total_tokens", 0) or (prompt + completion))
        return LLMUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )
    except Exception:
        return LLMUsage()


def merge_token_usage(existing: dict | None, usage: LLMUsage) -> dict[str, int]:
    """Sum usage into a TravelState-style token_usage dict."""
    base = existing if isinstance(existing, dict) else {}
    return {
        "prompt_tokens": int(base.get("prompt_tokens") or 0) + usage.prompt_tokens,
        "completion_tokens": int(base.get("completion_tokens") or 0)
        + usage.completion_tokens,
        "total_tokens": int(base.get("total_tokens") or 0) + usage.total_tokens,
    }


def _emit_generation_span(
    *,
    name: str,
    model: str,
    usage: LLMUsage,
    latency_ms: float,
    retry_count: int,
) -> None:
    """Best-effort Langfuse generation span; never raises."""
    try:
        from src.core.observability.tracing import safe_generation_span

        safe_generation_span(
            name=name,
            model=model,
            usage=usage,
            latency_ms=latency_ms,
            retry_count=retry_count,
        )
    except Exception:
        pass


@dataclass
class LLMToolResponse:
    tool_calls: list[dict]
    content: str | None
    usage: LLMUsage = field(default_factory=LLMUsage)
    retry_count: int = 0


@_llm_retry
async def _chat_completion_inner(
    messages: list[dict],
    model: str | None = None,
    response_format: dict | None = None,
) -> tuple[str, LLMUsage, str]:
    settings = get_settings()
    api_key = _require_llm_api_key(settings)
    resolved_model = model or settings.LLM_MODEL
    try:
        response = await litellm.acompletion(
            model=resolved_model,
            messages=messages,
            response_format=response_format,
            api_key=api_key,
            api_base=settings.LLM_API_BASE or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        content = response.choices[0].message.content
        return (
            (content if content is not None else ""),
            _usage_from_response(response),
            resolved_model,
        )
    except litellm.RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except litellm.Timeout:
        raise
    except WandrLLMError:
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    response_format: dict | None = None,
) -> ChatCompletionResult:
    _retry_bumps.set(0)
    started = time.perf_counter()
    settings = get_settings()
    resolved_model = model or settings.LLM_MODEL
    try:
        content, usage, resolved_model = await _chat_completion_inner(
            messages, model=model, response_format=response_format
        )
        retries = _retry_bumps.get()
        _emit_generation_span(
            name="chat_completion",
            model=resolved_model,
            usage=usage,
            latency_ms=(time.perf_counter() - started) * 1000,
            retry_count=retries,
        )
        return ChatCompletionResult(content=content, usage=usage, retry_count=retries)
    except Exception:
        _emit_generation_span(
            name="chat_completion",
            model=resolved_model,
            usage=LLMUsage(),
            latency_ms=(time.perf_counter() - started) * 1000,
            retry_count=_retry_bumps.get(),
        )
        raise


@_llm_retry
async def _chat_with_tools_inner(
    messages: list[dict],
    tools: list[dict],
    tool_choice: str = "auto",
    model: str | None = None,
) -> tuple[LLMToolResponse, str]:
    settings = get_settings()
    api_key = _require_llm_api_key(settings)
    resolved_model = model or settings.LLM_MODEL
    try:
        response = await litellm.acompletion(
            model=resolved_model,
            messages=messages,
            api_key=api_key,
            api_base=settings.LLM_API_BASE or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            tools=tools,
            tool_choice=tool_choice,
        )
        usage = _usage_from_response(response)
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
            return (
                LLMToolResponse(tool_calls=tool_calls, content=None, usage=usage),
                resolved_model,
            )
        return (
            LLMToolResponse(
                tool_calls=[], content=message.content, usage=usage
            ),
            resolved_model,
        )
    except litellm.RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except litellm.Timeout:
        raise
    except WandrLLMError:
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"LLM call failed after retries: {type(e).__name__}",
        ) from e


async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_choice: str = "auto",
    model: str | None = None,
) -> LLMToolResponse:
    _retry_bumps.set(0)
    started = time.perf_counter()
    settings = get_settings()
    resolved_model = model or settings.LLM_MODEL
    try:
        result, resolved_model = await _chat_with_tools_inner(
            messages, tools, tool_choice=tool_choice, model=model
        )
        retries = _retry_bumps.get()
        result.retry_count = retries
        _emit_generation_span(
            name="chat_with_tools",
            model=resolved_model,
            usage=result.usage,
            latency_ms=(time.perf_counter() - started) * 1000,
            retry_count=retries,
        )
        return result
    except Exception:
        _emit_generation_span(
            name="chat_with_tools",
            model=resolved_model,
            usage=LLMUsage(),
            latency_ms=(time.perf_counter() - started) * 1000,
            retry_count=_retry_bumps.get(),
        )
        raise


@_llm_retry
async def _embed_texts_inner(
    texts: list[str],
    model: str | None = None,
) -> tuple[list[list[float]], LLMUsage, str]:
    if not texts:
        return [], LLMUsage(), (model or get_settings().PLACES_EMBEDDING_MODEL)
    settings = get_settings()
    api_key = _require_embedding_api_key(settings)
    try:
        embed_model = model or settings.PLACES_EMBEDDING_MODEL
        response = await litellm.aembedding(
            model=embed_model,
            input=texts,
            api_key=api_key,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            dimensions=settings.PLACES_EMBEDDING_DIM,
        )

        def _index(row: object) -> int:
            if isinstance(row, dict):
                return int(row["index"])
            return int(getattr(row, "index"))

        def _embedding(row: object) -> list[float]:
            raw = (
                row["embedding"] if isinstance(row, dict) else getattr(row, "embedding")
            )
            return list(raw)

        data = sorted(response.data, key=_index)
        return (
            [_embedding(row) for row in data],
            _usage_from_response(response),
            embed_model,
        )
    except litellm.RateLimitError as e:
        retry_after = getattr(e, "retry_after", None) or 5
        await asyncio.sleep(float(retry_after))
        raise
    except litellm.Timeout:
        raise
    except WandrLLMError:
        raise
    except Exception as e:
        raise WandrLLMError(
            code="llm_unavailable",
            message=f"Embedding call failed after retries: {type(e).__name__}",
        ) from e


async def embed_texts(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Hosted embeddings via LiteLLM. Return type unchanged (list of vectors)."""
    _retry_bumps.set(0)
    started = time.perf_counter()
    vectors, usage, embed_model = await _embed_texts_inner(texts, model=model)
    retries = _retry_bumps.get()
    _emit_generation_span(
        name="embed_texts",
        model=embed_model,
        usage=usage,
        latency_ms=(time.perf_counter() - started) * 1000,
        retry_count=retries,
    )
    return vectors
