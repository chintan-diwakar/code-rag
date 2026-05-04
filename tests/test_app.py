"""Tests for the FastAPI app routes.

We avoid loading the real flask source + embedder by building a tiny stub
pipeline from the test fixture and patching `Pipeline.build` to return it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from code_rag import app as app_module
from code_rag.chunker_ast import chunk_python_file
from code_rag.pipeline import Pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "sample.py"


class _StubEmbedder:
    """Deterministic embedder that hashes text to a fixed-dim vector.

    Avoids downloading bge-small (~130MB) and the ~2s model-load cost.
    """

    model_name = "stub-embedder"
    dim = 16

    def encode(self, texts, batch_size: int = 32) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            out[i] = rng.standard_normal(self.dim).astype(np.float32)
        return out


@pytest.fixture(scope="module")
def stub_pipeline() -> Pipeline:
    chunks = chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"))
    embedder = _StubEmbedder()
    embeddings = embedder.encode([c.code for c in chunks])
    return Pipeline(chunks=chunks, embeddings=embeddings, embedder=embedder)


@pytest.fixture
def client(monkeypatch, stub_pipeline) -> TestClient:
    monkeypatch.setattr(Pipeline, "build", classmethod(lambda cls: stub_pipeline))
    test_app = app_module.create_app()
    with TestClient(test_app) as c:
        yield c


def test_index_renders(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "code-rag" in body
    assert "<input" in body
    assert "name=\"q\"" in body
    # Mode dropdown should have all three options.
    for mode in ("vector", "bm25", "hybrid"):
        assert f">{mode}<" in body


def test_healthz_reports_pipeline(client: TestClient, stub_pipeline: Pipeline) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["n_chunks"] == len(stub_pipeline.chunks)
    assert payload["model"] == "stub-embedder"
    assert set(payload["modes"]) == {"vector", "bm25", "hybrid"}


def test_search_bm25_returns_html_fragment(client: TestClient) -> None:
    r = client.post("/search", data={"q": "greet", "mode": "bm25", "k": 3})
    assert r.status_code == 200
    body = r.text
    # Fragment, not a full page
    assert "<html" not in body.lower()
    assert "mode=" in body
    assert "Greeter" in body or "greet" in body


def test_search_vector_uses_query_embedding(client: TestClient) -> None:
    r = client.post("/search", data={"q": "async function", "mode": "vector", "k": 5})
    assert r.status_code == 200
    body = r.text
    assert "mode=" in body
    # Should render at least one result card with a file path.
    assert "fixtures/sample.py" in body or "sample.py" in body


def test_search_hybrid_smoke(client: TestClient) -> None:
    r = client.post("/search", data={"q": "greet by name", "mode": "hybrid", "k": 5})
    assert r.status_code == 200
    assert "mode=" in r.text


def test_search_invalid_mode_falls_back_to_hybrid(client: TestClient) -> None:
    r = client.post("/search", data={"q": "greet", "mode": "wat", "k": 3})
    assert r.status_code == 200
    assert "mode=<strong" in r.text and "hybrid" in r.text


def test_search_clamps_k(client: TestClient) -> None:
    r = client.post("/search", data={"q": "greet", "mode": "bm25", "k": 9999})
    assert r.status_code == 200
    # k is clamped to 20, and only as many as we have chunks.
    assert "k=20" in r.text


def test_search_empty_query_returns_no_results_card(client: TestClient) -> None:
    r = client.post("/search", data={"q": "   ", "mode": "bm25", "k": 5})
    assert r.status_code == 200
    assert "No results" in r.text
