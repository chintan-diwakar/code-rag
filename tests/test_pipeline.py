"""Tests for the Pipeline disk cache + search dispatch.

Fast: builds chunks from one fixture file, embeds with a stub, persists +
re-loads cache from a tmp_path.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from code_rag.chunker_ast import chunk_python_file
from code_rag.pipeline import Pipeline, _fingerprint, _load_or_build_cache

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURE_DIR / "sample.py"


class _StubEmbedder:
    model_name = "stub-embedder"
    dim = 8
    encode_calls = 0

    def encode(self, texts, batch_size: int = 32) -> np.ndarray:
        type(self).encode_calls += 1
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            out[i] = rng.standard_normal(self.dim).astype(np.float32)
        return out


@pytest.fixture
def chunks():
    return chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"))


def test_pipeline_search_dispatches_by_mode(chunks):
    embedder = _StubEmbedder()
    embeddings = embedder.encode([c.code for c in chunks])
    pipe = Pipeline(chunks=chunks, embeddings=embeddings, embedder=embedder)

    for mode in ("vector", "bm25", "hybrid"):
        resp = pipe.search("greet by name", mode=mode, k=3)
        assert resp.mode == mode
        assert resp.k == 3
        assert resp.latency_ms >= 0.0
        assert len(resp.hits) >= 1


def test_pipeline_unknown_mode_raises(chunks):
    embedder = _StubEmbedder()
    embeddings = embedder.encode([c.code for c in chunks])
    pipe = Pipeline(chunks=chunks, embeddings=embeddings, embedder=embedder)
    with pytest.raises(ValueError):
        pipe.search("x", mode="lexical")


def test_pipeline_empty_query_returns_no_hits(chunks):
    embedder = _StubEmbedder()
    embeddings = embedder.encode([c.code for c in chunks])
    pipe = Pipeline(chunks=chunks, embeddings=embeddings, embedder=embedder)
    resp = pipe.search("   ", mode="bm25")
    assert resp.hits == []


def test_cache_roundtrip_skips_re_embed(tmp_path, chunks):
    cache_path = tmp_path / "index.npz"
    embedder = _StubEmbedder()
    fp = "test-fingerprint"

    _StubEmbedder.encode_calls = 0
    e1 = _load_or_build_cache(cache_path, chunks, embedder, "stub-embedder", fp)
    first_calls = _StubEmbedder.encode_calls
    assert cache_path.exists()
    assert e1.shape == (len(chunks), 8)

    e2 = _load_or_build_cache(cache_path, chunks, embedder, "stub-embedder", fp)
    # Cache hit: no additional encode call.
    assert _StubEmbedder.encode_calls == first_calls
    np.testing.assert_array_equal(e1, e2)


def test_cache_invalidates_when_fingerprint_changes(tmp_path, chunks):
    cache_path = tmp_path / "index.npz"
    embedder = _StubEmbedder()

    _StubEmbedder.encode_calls = 0
    _load_or_build_cache(cache_path, chunks, embedder, "stub-embedder", "fp-A")
    after_first = _StubEmbedder.encode_calls

    _load_or_build_cache(cache_path, chunks, embedder, "stub-embedder", "fp-B")
    # Fingerprint changed — must re-embed.
    assert _StubEmbedder.encode_calls > after_first


def test_cache_invalidates_when_model_changes(tmp_path, chunks):
    cache_path = tmp_path / "index.npz"
    embedder = _StubEmbedder()

    _StubEmbedder.encode_calls = 0
    _load_or_build_cache(cache_path, chunks, embedder, "model-A", "fp-1")
    after_first = _StubEmbedder.encode_calls

    _load_or_build_cache(cache_path, chunks, embedder, "model-B", "fp-1")
    assert _StubEmbedder.encode_calls > after_first


def test_fingerprint_changes_on_file_edit(tmp_path):
    src = tmp_path / "pkg"
    src.mkdir()
    (src / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    fp1 = _fingerprint(src)

    # Re-write with a different size (not just touch — mtime resolution on Windows
    # is coarse; size diff guarantees a different fingerprint).
    (src / "a.py").write_text("def foo():\n    return 999\n", encoding="utf-8")
    fp2 = _fingerprint(src)
    assert fp1 != fp2
