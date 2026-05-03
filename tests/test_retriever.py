"""Tests for retrievers. Uses synthetic vectors — no embedding model required."""

import numpy as np
import pytest

from vishanti.chunker_ast import CodeChunk
from vishanti.retriever import (
    BM25Retriever,
    HybridRetriever,
    InMemoryRetriever,
    VectorRetriever,
    tokenize_code,
)


def _chunk(name: str, code: str | None = None) -> CodeChunk:
    return CodeChunk(
        file_path="x.py",
        symbol_name=name,
        symbol_kind="function",
        start_line=1,
        end_line=2,
        code=code if code is not None else f"def {name}(): pass",
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


def test_in_memory_retriever_is_alias_for_vector() -> None:
    assert InMemoryRetriever is VectorRetriever


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


def test_tokenize_splits_snake_case() -> None:
    assert tokenize_code("register_blueprint(app)") == ["register", "blueprint", "app"]


def test_tokenize_splits_camel_case() -> None:
    assert tokenize_code("FlaskClient.openSession") == ["flask", "client", "open", "session"]


def test_tokenize_splits_acronym_then_camel() -> None:
    # XMLParser -> [XML, Parser]
    assert tokenize_code("XMLParser") == ["xml", "parser"]


def test_tokenize_handles_punctuation_and_numbers() -> None:
    assert tokenize_code("self.view_functions[rule.endpoint](**view_args)") == [
        "self",
        "view",
        "functions",
        "rule",
        "endpoint",
        "view",
        "args",
    ]


def test_tokenize_empty() -> None:
    assert tokenize_code("") == []
    assert tokenize_code("   !@#$  ") == []


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------


def test_bm25_finds_query_term_match() -> None:
    chunks = [
        _chunk("alpha", code="def alpha(): pass\n# random words about cats"),
        _chunk("beta", code="def register_blueprint(): pass\n# blueprint registration"),
        _chunk("gamma", code="def gamma(): pass\n# unrelated dogs"),
    ]
    retriever = BM25Retriever(chunks)
    hits = retriever.search("how to register a blueprint", k=3)
    assert hits[0].chunk.symbol_name == "beta"
    assert hits[0].score > hits[1].score


def test_bm25_handles_empty_query() -> None:
    chunks = [_chunk("a"), _chunk("b")]
    retriever = BM25Retriever(chunks)
    assert retriever.search("", k=5) == []


def test_bm25_returns_at_most_k() -> None:
    chunks = [_chunk(name, code=f"def {name}(): foo bar baz") for name in "abcde"]
    retriever = BM25Retriever(chunks)
    hits = retriever.search("foo", k=2)
    assert len(hits) == 2


# ---------------------------------------------------------------------------
# Hybrid (RRF)
# ---------------------------------------------------------------------------


def test_hybrid_combines_both_retrievers() -> None:
    # Three chunks. Chunk A wins on vector, chunk B wins on BM25.
    # RRF should rank both above unrelated chunk C.
    chunks = [
        _chunk("a", code="def alpha(): pass"),
        _chunk("b", code="def register_blueprint(): pass"),
        _chunk("c", code="def gamma(): random unrelated text"),
    ]
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],  # A — query vector matches this
            [0.0, 1.0, 0.0],  # B
            [0.0, 0.0, 1.0],  # C
        ],
        dtype=np.float32,
    )
    vector = VectorRetriever(embeddings, chunks)
    bm25 = BM25Retriever(chunks)
    hybrid = HybridRetriever(vector, bm25, fetch_k=3, c=60)

    hits = hybrid.search("register blueprint", np.array([1.0, 0.0, 0.0]), k=3)
    names = [h.chunk.symbol_name for h in hits]
    # Both A (vector winner) and B (bm25 winner) should beat C.
    assert "c" not in names[:2], names


def test_hybrid_rrf_score_formula() -> None:
    # When the same chunk wins both retrievers at rank 0, its RRF score should
    # be exactly 2 / (c + 1).
    chunks = [_chunk("a", code="def foo(): pass")]
    embeddings = np.array([[1.0]], dtype=np.float32)
    vector = VectorRetriever(embeddings, chunks)
    bm25 = BM25Retriever(chunks)
    hybrid = HybridRetriever(vector, bm25, fetch_k=1, c=60)

    hits = hybrid.search("foo", np.array([1.0]), k=1)
    assert len(hits) == 1
    assert hits[0].score == pytest.approx(2.0 / (60 + 1))
