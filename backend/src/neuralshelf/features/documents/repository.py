"""Database operations for documents and chunks."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from neuralshelf.features.documents.chunking import TextChunk
from neuralshelf.features.documents.models import Chunk, Document


class DocumentRepository:
    """Encapsulate database access for documents and their chunks.

    Every user-facing read and delete is scoped by ``user_id``.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, document: Document) -> Document:
        """Insert a document (flushed, not committed)."""
        self.db.add(document)
        self.db.flush()
        return document

    def get_owned(self, *, user_id: UUID, document_id: UUID) -> Document | None:
        """The document if it exists and belongs to ``user_id``, else None."""
        statement = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get(self, document_id: UUID) -> Document | None:
        """Unscoped lookup; for background ingestion only."""
        return self.db.get(Document, document_id)

    def list_owned(
        self, *, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]:
        """The user's documents, newest first, and their total count."""
        statement = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc(), Document.id)
            .limit(limit)
            .offset(offset)
        )
        total = self.db.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == user_id)
        )
        return self.db.scalars(statement).all(), total or 0

    def delete(self, document: Document) -> None:
        """Delete a document; its chunks and jobs go with it (ON DELETE CASCADE)."""
        # chunks are removed by the ON DELETE CASCADE foreign key.
        self.db.execute(delete(Document).where(Document.id == document.id))

    def replace_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[TextChunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        """Replace all of a document's chunks with ``chunks`` and their ``embeddings``."""
        self.db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        if chunks:
            self.db.execute(
                insert(Chunk),
                [
                    {
                        "document_id": document_id,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "content": chunk.content,
                        "embedding": embedding,
                    }
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ],
            )

