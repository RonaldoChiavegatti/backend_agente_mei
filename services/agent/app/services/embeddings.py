"""Lightweight embedding utilities used by the Agent service."""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, List


class LocalEmbeddingClient:
    """Deterministic embedding generator for offline environments."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_query(self, text: str) -> List[float]:
        """Generate an embedding vector for a query string."""

        return self._embed(text)

    def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        """Generate embeddings for a sequence of document texts."""

        return [self._embed(text) for text in texts]

    def cosine_similarity(self, a: Iterable[float], b: Iterable[float]) -> float:
        """Compute the cosine similarity between two vectors."""

        vec_a = list(a)
        vec_b = list(b)

        if len(vec_a) != len(vec_b):
            raise ValueError("Vector sizes must match for cosine similarity")

        dot_product = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(x * x for x in vec_a))
        norm_b = math.sqrt(sum(y * y for y in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def _embed(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        byte_values = list(digest)

        vector: List[float] = []
        index = 0
        while len(vector) < self.dimension:
            value = byte_values[index % len(byte_values)]
            normalized = (value / 255.0) * 2 - 1
            vector.append(normalized)
            index += 1

        return vector[: self.dimension]
