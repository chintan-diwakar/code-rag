"""Tests for the embedder. Uses the real bge-small model (cached after first run)."""

import numpy as np
import pytest

from vishanti.embedder import DEFAULT_MODEL, Embedder


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder()


def test_default_model_name(embedder: Embedder) -> None:
    assert embedder.model_name == DEFAULT_MODEL


def test_dim_is_384_for_bge_small(embedder: Embedder) -> None:
    assert embedder.dim == 384


def test_encode_returns_correct_shape(embedder: Embedder) -> None:
    vectors = embedder.encode(["hello world", "another text", "third one"])
    assert vectors.shape == (3, 384)
    assert vectors.dtype == np.float32


def test_encode_empty_returns_empty_array(embedder: Embedder) -> None:
    vectors = embedder.encode([])
    assert vectors.shape == (0, 384)


def test_encode_is_deterministic(embedder: Embedder) -> None:
    a = embedder.encode(["the quick brown fox"])
    b = embedder.encode(["the quick brown fox"])
    np.testing.assert_allclose(a, b, rtol=1e-5)


def test_semantic_similarity_is_meaningful(embedder: Embedder) -> None:
    # A trivially correct semantic test: synonymous phrases should be more
    # similar than unrelated phrases.
    vectors = embedder.encode(
        [
            "how to register a blueprint with the application",
            "registering blueprints in flask",
            "the price of bananas in 2024",
        ]
    )
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normed = vectors / norms

    sim_related = float(normed[0] @ normed[1])
    sim_unrelated = float(normed[0] @ normed[2])
    assert sim_related > sim_unrelated, (sim_related, sim_unrelated)
