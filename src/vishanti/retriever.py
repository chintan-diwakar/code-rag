"""Retrievers for the RAG pipeline.

- VectorRetriever: in-memory cosine similarity over L2-normalized embeddings.
- BM25Retriever: classic BM25 with code-aware tokenization (camelCase splits).
- HybridRetriever: combines vector + BM25 via Reciprocal Rank Fusion (RRF).

All three share the same `chunks` list and return `RetrievalHit` for a
uniform downstream interface.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from vishanti.chunker_ast import CodeChunk

# Backwards-compatible alias used by older tests / scripts.
__all__ = [
    "BM25Retriever",
    "HybridRetriever",
    "InMemoryRetriever",
    "RetrievalHit",
    "VectorRetriever",
    "tokenize_code",
]


@dataclass
class RetrievalHit:
    chunk: CodeChunk
    score: float
    rank: int  # 0-indexed rank in the result list


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------


class VectorRetriever:
    """L2-normalize at index time so cosine similarity reduces to dot product."""

    def __init__(self, embeddings: np.ndarray, chunks: list[CodeChunk]) -> None:
        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"embeddings.shape[0]={embeddings.shape[0]} != len(chunks)={len(chunks)}"
            )
        self.chunks = chunks
        self.embeddings = _l2_normalize(embeddings)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> list[RetrievalHit]:
        if query_embedding.ndim != 1:
            raise ValueError(f"query_embedding must be 1-D, got shape {query_embedding.shape}")
        if k <= 0:
            return []
        q = query_embedding / max(float(np.linalg.norm(query_embedding)), 1e-8)
        scores = self.embeddings @ q
        return _top_k(self.chunks, scores, k)


# Alias for backwards compatibility with the day-1 commit.
InMemoryRetriever = VectorRetriever


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z]*|\d+")
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize_code(text: str) -> list[str]:
    """Tokenize source/text for BM25.

    - Split on non-alphanumeric (so `_` and `.` are delimiters).
    - Split camelCase / PascalCase into subtokens.
    - Lowercase. Drop empty.

    Example: `register_blueprint(MyApp)` -> ['register', 'blueprint', 'my', 'app'].
    """
    out: list[str] = []
    for raw in _WORD_RE.findall(text):
        for sub in _CAMEL_SPLIT_RE.split(raw):
            if sub:
                out.append(sub.lower())
    return out


class BM25Retriever:
    """Okapi BM25 with the BM25+ idf variant (no negative idf for common terms).

    Brute force scoring — fine for week-1's ~300 chunks. For larger corpora
    swap in an inverted-index implementation.
    """

    def __init__(
        self,
        chunks: list[CodeChunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self.doc_tokens: list[list[str]] = [tokenize_code(c.code) for c in chunks]
        self.doc_lens = np.array([len(t) for t in self.doc_tokens], dtype=np.float32)
        self.avg_dl = float(self.doc_lens.mean()) if len(chunks) else 0.0
        self.N = len(chunks)

        self.term_freq: list[dict[str, int]] = []
        self.doc_freq: dict[str, int] = {}
        for tokens in self.doc_tokens:
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.term_freq.append(tf)
            for term in tf:
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        # BM25+ idf: log((N - df + 0.5) / (df + 0.5) + 1) — strictly non-negative.
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, k: int = 5) -> list[RetrievalHit]:
        query_terms = tokenize_code(query)
        if not query_terms or self.N == 0:
            return []

        scores = np.zeros(self.N, dtype=np.float32)
        for term in query_terms:
            idf = self._idf(term)
            if idf <= 0:
                continue
            for i, tf_dict in enumerate(self.term_freq):
                tf = tf_dict.get(term, 0)
                if tf == 0:
                    continue
                dl = self.doc_lens[i]
                norm = 1.0 - self.b + self.b * (dl / self.avg_dl) if self.avg_dl > 0 else 1.0
                scores[i] += idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * norm)

        return _top_k(self.chunks, scores, k)


# ---------------------------------------------------------------------------
# Hybrid (Reciprocal Rank Fusion)
# ---------------------------------------------------------------------------


class HybridRetriever:
    """Combine vector + BM25 via Reciprocal Rank Fusion.

    RRF score for a doc d:
        score(d) = sum over rankers of 1 / (c + rank_in_ranker(d))

    Default c=60 is the value from the original RRF paper. fetch_k controls
    how many candidates each underlying retriever returns before fusion;
    larger fetch_k = better recall, slower.
    """

    def __init__(
        self,
        vector: VectorRetriever,
        bm25: BM25Retriever,
        *,
        c: int = 60,
        fetch_k: int = 20,
    ) -> None:
        self.vector = vector
        self.bm25 = bm25
        self.c = c
        self.fetch_k = fetch_k

    def search(
        self, query: str, query_embedding: np.ndarray, k: int = 5
    ) -> list[RetrievalHit]:
        vec_hits = self.vector.search(query_embedding, k=self.fetch_k)
        bm25_hits = self.bm25.search(query, k=self.fetch_k)

        rrf: dict[int, float] = {}
        chunks_by_id: dict[int, CodeChunk] = {}
        for hit in vec_hits:
            cid = id(hit.chunk)
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (self.c + hit.rank + 1)
            chunks_by_id[cid] = hit.chunk
        for hit in bm25_hits:
            cid = id(hit.chunk)
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (self.c + hit.rank + 1)
            chunks_by_id[cid] = hit.chunk

        ordered_ids = sorted(rrf, key=lambda i: -rrf[i])
        return [
            RetrievalHit(chunks_by_id[cid], rrf[cid], rank)
            for rank, cid in enumerate(ordered_ids[:k])
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms > 0, norms, 1.0)


def _top_k(chunks: list[CodeChunk], scores: np.ndarray, k: int) -> list[RetrievalHit]:
    if k <= 0 or len(chunks) == 0:
        return []
    k = min(k, len(scores))
    top_unsorted = np.argpartition(-scores, k - 1)[:k]
    top_sorted = top_unsorted[np.argsort(-scores[top_unsorted])]
    return [
        RetrievalHit(chunks[int(i)], float(scores[int(i)]), rank)
        for rank, i in enumerate(top_sorted)
    ]
