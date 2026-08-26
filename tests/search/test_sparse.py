"""Unit tests for pure-Python sparse encoder."""

from __future__ import annotations

import pytest
from qdrant_client import models as qmodels

from src.search import sparse as sparse_mod
from src.search.sparse import (
    encode_sparse,
    encode_sparse_batch,
    is_sparse_available,
)


@pytest.fixture(autouse=True)
def _reset_sparse_gate() -> None:
    sparse_mod._set_sparse_available(True)
    yield
    sparse_mod._set_sparse_available(True)


def test_encode_sparse_empty_text_returns_empty_vector() -> None:
    vec = encode_sparse("")
    assert isinstance(vec, qmodels.SparseVector)
    assert vec.indices == []
    assert vec.values == []
    assert is_sparse_available() is True


def test_encode_sparse_includes_name_tokens() -> None:
    vec = encode_sparse("Tiger Hill viewpoint")
    assert vec.indices
    assert len(vec.indices) == len(vec.values)
    assert all(v > 0 for v in vec.values)


def test_encode_sparse_drops_stopwords() -> None:
    with_stops = encode_sparse("the hill and the view")
    no_stops = encode_sparse("hill view")
    assert set(with_stops.indices) == set(no_stops.indices)


@pytest.mark.asyncio
async def test_encode_sparse_batch_parallel_array() -> None:
    out = await encode_sparse_batch(["Tiger Hill", "", "Batasia Loop"])
    assert len(out) == 3
    assert out[0].indices
    assert out[1].indices == []
    assert out[2].indices


def test_encode_sparse_failure_marks_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_text: str) -> list[str]:
        raise RuntimeError("tokenize boom")

    monkeypatch.setattr(sparse_mod, "_tokenize", boom)
    vec = encode_sparse("anything")
    assert vec.indices == []
    assert is_sparse_available() is False
    # Subsequent calls stay empty without raising
    assert encode_sparse("again").indices == []
