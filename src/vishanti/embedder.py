"""Text embedder. Wraps fastembed (ONNX runtime — no PyTorch dependency).

Default model: BAAI/bge-small-en-v1.5 (33M params, 384-dim, ~130MB on disk).
Larger model BAAI/bge-large-en-v1.5 (1.3GB, 1024-dim) can be selected per
ablation studies in week 2.

The model downloads from HuggingFace on the first `Embedder(...)` call and
caches under ~/.cache/fastembed. Subsequent runs are instant.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
from fastembed import TextEmbedding

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    @property
    def dim(self) -> int:
        # bge-small=384, bge-large=1024. Encode a sentinel to discover.
        if not hasattr(self, "_dim"):
            sample = next(iter(self._model.embed(["dim probe"])))
            self._dim = int(sample.shape[0])
        return self._dim

    def encode(self, texts: Iterable[str], batch_size: int = 32) -> np.ndarray:
        """Embed a batch of texts. Returns shape (N, dim) float32 array."""
        texts_list = list(texts)
        if not texts_list:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = list(self._model.embed(texts_list, batch_size=batch_size))
        return np.stack(vectors).astype(np.float32)
