"""FastAPI dependencies that provide configured provider clients.

Override these in tests to avoid calling a live Ollama server.
"""

from functools import lru_cache

from neuralshelf.core.config import get_settings
from neuralshelf.integrations.embeddings.ollama import EmbeddingClient, OllamaEmbeddingClient
from neuralshelf.integrations.llm.ollama import ChatClient, OllamaChatClient


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    """The configured embedding client (cached). Tests override this dependency."""
    settings = get_settings()
    return OllamaEmbeddingClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        document_prefix=settings.embedding_document_prefix,
        query_prefix=settings.embedding_query_prefix,
    )


@lru_cache
def get_chat_client() -> ChatClient:
    """The configured chat model client (cached). Tests override this dependency."""
    settings = get_settings()
    return OllamaChatClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_chat_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
