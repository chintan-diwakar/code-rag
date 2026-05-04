"""Singleton pipeline for the FastAPI app.

Loads chunks once at startup, embeds them (with a disk cache so server
restarts are instant), and exposes a unified `search()` over vector / bm25 /
hybrid retrieval modes.

Cache layout: `data/cache/index.npz`
    embeddings : (N, dim) float32
    model      : str
    fingerprint: str  (hash of source files' size+mtime)

If the source tree or model changes, the cache is rebuilt.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from code_rag.chunker_ast import CodeChunk, chunk_python_file
from code_rag.embedder import DEFAULT_MODEL, Embedder
from code_rag.retriever import (
    BM25Retriever,
    HybridRetriever,
    RetrievalHit,
    VectorRetriever,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = REPO_ROOT / "data" / "flask" / "src" / "flask"
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "cache" / "index.npz"

VALID_MODES = ("vector", "bm25", "hybrid")


@dataclass
class SearchResponse:
    mode: str
    query: str
    k: int
    latency_ms: float
    hits: list[RetrievalHit]


class Pipeline:
    def __init__(
        self,
        chunks: list[CodeChunk],
        embeddings: np.ndarray,
        embedder: Embedder,
    ) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.embedder = embedder
        self.vector = VectorRetriever(embeddings, chunks)
        self.bm25 = BM25Retriever(chunks)
        self.hybrid = HybridRetriever(self.vector, self.bm25)

    @classmethod
    def build(
        cls,
        source_dir: Path = DEFAULT_SOURCE_DIR,
        cache_path: Path = DEFAULT_CACHE_PATH,
        model_name: str = DEFAULT_MODEL,
    ) -> "Pipeline":
        if not source_dir.exists():
            raise FileNotFoundError(
                f"missing source dir: {source_dir}\n"
                f"clone first: git clone --depth 1 https://github.com/pallets/flask.git data/flask"
            )

        chunks = _chunk_repo(source_dir)
        fingerprint = _fingerprint(source_dir)

        embedder = Embedder(model_name=model_name)
        embeddings = _load_or_build_cache(
            cache_path, chunks, embedder, model_name, fingerprint
        )
        return cls(chunks=chunks, embeddings=embeddings, embedder=embedder)

    def search(self, query: str, mode: str = "hybrid", k: int = 5) -> SearchResponse:
        if mode not in VALID_MODES:
            raise ValueError(f"unknown mode {mode!r}; expected one of {VALID_MODES}")
        if not query.strip():
            return SearchResponse(mode=mode, query=query, k=k, latency_ms=0.0, hits=[])

        t0 = time.perf_counter()
        if mode == "bm25":
            hits = self.bm25.search(query, k=k)
        else:
            qv = self.embedder.encode([query])[0]
            if mode == "vector":
                hits = self.vector.search(qv, k=k)
            else:  # hybrid
                hits = self.hybrid.search(query, qv, k=k)
        latency = (time.perf_counter() - t0) * 1000.0
        return SearchResponse(mode=mode, query=query, k=k, latency_ms=latency, hits=hits)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _chunk_repo(src_dir: Path) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for path in sorted(src_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        # Path stored as `flask/foo.py` for human-readable display.
        rel = path.relative_to(src_dir.parents[1])
        for c in chunk_python_file(str(rel).replace("\\", "/"), text):
            chunks.append(c)
    return chunks


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------


def _fingerprint(src_dir: Path) -> str:
    """Hash size+mtime of every .py file under src_dir.

    Cheap and good enough — a real edit changes mtime; pure-rename is rare in
    a vendored read-only checkout.
    """
    h = hashlib.sha256()
    for path in sorted(src_dir.rglob("*.py")):
        st = path.stat()
        h.update(str(path.relative_to(src_dir)).encode("utf-8"))
        h.update(str(st.st_size).encode("ascii"))
        h.update(str(int(st.st_mtime)).encode("ascii"))
    return h.hexdigest()


def _load_or_build_cache(
    cache_path: Path,
    chunks: list[CodeChunk],
    embedder: Embedder,
    model_name: str,
    fingerprint: str,
) -> np.ndarray:
    if cache_path.exists():
        try:
            data = np.load(cache_path, allow_pickle=False)
            cached_model = str(data["model"])
            cached_fp = str(data["fingerprint"])
            cached_n = int(data["n_chunks"])
            if (
                cached_model == model_name
                and cached_fp == fingerprint
                and cached_n == len(chunks)
            ):
                return data["embeddings"].astype(np.float32)
        except (KeyError, ValueError, OSError):
            pass  # corrupt or wrong-shape cache — rebuild.

    embeddings = embedder.encode([c.code for c in chunks])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        cache_path,
        embeddings=embeddings,
        model=np.array(model_name),
        fingerprint=np.array(fingerprint),
        n_chunks=np.array(len(chunks)),
    )
    return embeddings


# ---------------------------------------------------------------------------
# Lazy global accessor (used by FastAPI lifespan)
# ---------------------------------------------------------------------------


_PIPELINE: Pipeline | None = None


def get_pipeline() -> Pipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = Pipeline.build()
    return _PIPELINE


def set_pipeline(pipeline: Pipeline | None) -> None:
    """Used by FastAPI lifespan and tests."""
    global _PIPELINE
    _PIPELINE = pipeline
