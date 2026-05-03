"""In-memory cosine-similarity retriever.

For week 1 baseline. pgvector backend lands in week 2 — same interface so the
eval runner doesn't change.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vishanti.chunker_ast import CodeChunk


@dataclass
class RetrievalHit:
    chunk: CodeChunk
    score: float
    rank: int  # 0-indexed rank in the result list


class InMemoryRetriever:
    """Stores L2-normalized embeddings so cosine similarity = dot product."""

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
        scores = self.embeddings @ q  # (N,)

        k = min(k, len(scores))
        # argpartition then sort just the top-k slice — O(N + k log k) vs O(N log N)
        top_unsorted = np.argpartition(-scores, k - 1)[:k]
        top_sorted = top_unsorted[np.argsort(-scores[top_unsorted])]

        return [
            RetrievalHit(chunk=self.chunks[int(i)], score=float(scores[int(i)]), rank=rank)
            for rank, i in enumerate(top_sorted)
        ]


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms > 0, norms, 1.0)
