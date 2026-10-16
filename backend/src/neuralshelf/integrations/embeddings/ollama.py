"""Ollama embedding client."""

import logging
from typing import Protocol

import httpx

from neuralshelf.core.constants import EMBEDDING_DIMENSIONS
from neuralshelf.core.exceptions import EmbeddingServiceError

logger = logging.getLogger(__name__)


class EmbeddingClient(Protocol):
    """Anything that can embed document chunks and search queries."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages for storage."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query."""


class OllamaEmbeddingClient:
    """Embed text with a local Ollama embedding model via /api/embed."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        document_prefix: str = "",
        query_prefix: str = "",
        batch_size: int = 32,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.document_prefix = document_prefix
        self.query_prefix = query_prefix
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages in batches, with the model's document prefix."""
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            embeddings.extend(self._embed([f"{self.document_prefix}{t}" for t in batch]))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed one search query, with the model's query prefix."""
        return self._embed([f"{self.query_prefix}{text}"])[0]

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": inputs},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.exception("Ollama embedding request failed.")
            raise EmbeddingServiceError() from exc

        if len(embeddings) != len(inputs) or any(
            len(vector) != EMBEDDING_DIMENSIONS for vector in embeddings
        ):
            logger.error(
                "Embedding model %s returned unexpected shape; expected %d dimensions.",
                self.model,
                EMBEDDING_DIMENSIONS,
            )
            raise EmbeddingServiceError()

        return embeddings
