"""Tests for InMemoryRetriever. Uses synthetic vectors — no model required."""

import numpy as np
import pytest

from vishanti.chunker_ast import CodeChunk
from vishanti.retriever import InMemoryRetriever


def _chunk(name: str) -> CodeChunk:
    return CodeChunk(
        file_path="x.py",
        symbol_name=name,
        symbol_kind="function",
        start_line=1,
        end_line=2,
        code=f"def {name}(): pass",
    )


def test_self_retrieval_ranks_first() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    retriever = InMemoryRetriever(embeddings, chunks)

    hits = retriever.search(np.array([1.0, 0.0, 0.0]), k=3)
    assert [h.chunk.symbol_name for h in hits] == ["a", "b", "c"] or hits[0].chunk.symbol_name == "a"
    assert hits[0].rank == 0
    assert hits[0].score == pytest.approx(1.0)


def test_top_k_truncates() -> None:
    embeddings = np.eye(5, dtype=np.float32)
    chunks = [_chunk(c) for c in "abcde"]
    retriever = InMemoryRetriever(embeddings, chunks)

    hits = retriever.search(np.array([1.0, 0.5, 0.25, 0.1, 0.0]), k=2)
    assert len(hits) == 2
    assert hits[0].chunk.symbol_name == "a"
    assert hits[1].chunk.symbol_name == "b"
    assert hits[0].score >= hits[1].score


def test_k_larger_than_index_returns_all() -> None:
    embeddings = np.eye(2, dtype=np.float32)
    chunks = [_chunk("a"), _chunk("b")]
    retriever = InMemoryRetriever(embeddings, chunks)
    hits = retriever.search(np.array([1.0, 0.0]), k=10)
    assert len(hits) == 2


def test_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError, match="!= len"):
        InMemoryRetriever(np.zeros((3, 4), dtype=np.float32), [_chunk("a")])


def test_query_must_be_1d() -> None:
    embeddings = np.eye(2, dtype=np.float32)
    chunks = [_chunk("a"), _chunk("b")]
    retriever = InMemoryRetriever(embeddings, chunks)
    with pytest.raises(ValueError, match="must be 1-D"):
        retriever.search(np.array([[1.0, 0.0]]), k=1)


def test_zero_norm_query_does_not_crash() -> None:
    embeddings = np.eye(2, dtype=np.float32)
    chunks = [_chunk("a"), _chunk("b")]
    retriever = InMemoryRetriever(embeddings, chunks)
    hits = retriever.search(np.zeros(2, dtype=np.float32), k=2)
    assert len(hits) == 2  # ranking arbitrary but no exception
