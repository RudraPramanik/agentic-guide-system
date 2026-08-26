"""Pure-Python BM25-style sparse encoder for Qdrant named vector ``bm25``."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

import structlog
from qdrant_client import models as qmodels

log = structlog.get_logger()

_sparse_available: bool = True
_logged_unavailable: bool = False

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Small inline English set — keep minimal; do not pull NLTK.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "by",
        "from",
        "as",
        "it",
        "this",
        "that",
        "these",
        "those",
    }
)


def is_sparse_available() -> bool:
    """Fail-soft gate — mirrors embeddings.is_embeddings_available()."""
    return _sparse_available


def _set_sparse_available(value: bool) -> None:
    global _sparse_available, _logged_unavailable
    _sparse_available = value
    if value:
        _logged_unavailable = False


def _mark_unavailable(error: str) -> None:
    global _sparse_available, _logged_unavailable
    _sparse_available = False
    if not _logged_unavailable:
        log.warning("sparse.encode_unavailable", error=error)
        _logged_unavailable = True


def _tokenize(text: str) -> list[str]:
    return [
        t
        for t in _TOKEN_RE.findall(text.lower())
        if t not in _STOPWORDS and len(t) > 1
    ]


def _stable_term_index(term: str) -> int:
    digest = hashlib.md5(term.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31 - 1)


def _empty_sparse() -> qmodels.SparseVector:
    return qmodels.SparseVector(indices=[], values=[])


def encode_sparse(text: str) -> qmodels.SparseVector:
    """
    Query/document term weights without corpus IDF (MVP).
    Never raises — on failure marks sparse unavailable and returns empty vector.
    """
    if not _sparse_available:
        return _empty_sparse()
    try:
        tokens = _tokenize(text or "")
        if not tokens:
            return _empty_sparse()
        counts = Counter(tokens)
        merged: dict[int, float] = {}
        for term, tf in counts.items():
            idx = _stable_term_index(term)
            # 1 + log(tf) style weight without math.log for tiny counts
            weight = 1.0 + (tf - 1) * 0.5 if tf > 1 else 1.0
            merged[idx] = merged.get(idx, 0.0) + weight
        indices = sorted(merged.keys())
        values = [merged[i] for i in indices]
        return qmodels.SparseVector(indices=indices, values=values)
    except Exception as exc:
        _mark_unavailable(str(exc))
        return _empty_sparse()


async def encode_sparse_batch(texts: list[str]) -> list[qmodels.SparseVector]:
    """Parallel-array contract: one sparse vector per input text; never raises."""
    return [encode_sparse(text) for text in texts]
