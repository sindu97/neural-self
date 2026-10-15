"""Semantic search over the authenticated user's documents."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from neuralshelf.features.documents.exceptions import DocumentNotFoundError
from neuralshelf.features.retrieval.repository import RetrievalRepository
from neuralshelf.integrations.embeddings.ollama import EmbeddingClient


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: UUID
    filename: str
    chunk_index: int
    page_number: int | None
    content: str
    score: float


class RetrievalService:
    def __init__(self, db: Session, embedder: EmbeddingClient) -> None:
        self.repository = RetrievalRepository(db)
        self.embedder = embedder

    def search(
        self,
        *,
        user_id: UUID,
        query: str,
        top_k: int,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[RetrievedChunk]:
        """Rank the user's chunks by similarity to ``query``.

        Every requested document must belong to the user; otherwise the
        request fails with 404, the same as for a document that doesn't exist.
        """
        requested = set(document_ids or [])
        if requested:
            owned = self.repository.owned_document_ids(
                user_id=user_id, document_ids=list(requested)
            )
            if owned != requested:
                raise DocumentNotFoundError()

        query_embedding = self.embedder.embed_query(query)
        rows = self.repository.nearest_chunks(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=list(requested),
        )

        return [
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                filename=row.filename,
                chunk_index=row.chunk_index,
                page_number=row.page_number,
                content=row.content,
                # Cosine similarity, from 1 (identical) down to -1.
                score=round(1.0 - float(row.distance), 4),
            )
            for row in rows
        ]
