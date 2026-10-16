"""Read-only similarity queries over chunks.

Retrieval reads chunk data without owning the documents/chunks tables;
the documents feature remains responsible for writing them.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row, select, text
from sqlalchemy.orm import Session

from neuralshelf.features.documents.models import Chunk, Document, DocumentStatus


class RetrievalRepository:
    """Read-only similarity queries over chunks."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def owned_document_ids(self, *, user_id: UUID, document_ids: Sequence[UUID]) -> set[UUID]:
        """The subset of ``document_ids`` that belong to ``user_id``."""
        statement = select(Document.id).where(
            Document.user_id == user_id,
            Document.id.in_(document_ids),
        )
        return set(self.db.scalars(statement).all())

    def nearest_chunks(
        self,
        *,
        user_id: UUID,
        query_embedding: list[float],
        top_k: int,
        document_ids: Sequence[UUID] | None = None,
    ) -> Sequence[Row]:
        """Return the user's ``top_k`` chunks closest to the query by cosine distance.

        With the HNSW index, Postgres finds nearest neighbours across *all*
        users first and filters by owner afterwards, so a plain scan can
        return fewer than ``top_k`` rows. An iterative scan (pgvector >= 0.8)
        keeps searching the index until enough rows pass the filters;
        ``strict_order`` keeps the results exactly ordered by distance.
        """
        self.db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
        distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
        statement = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.chunk_index,
                Chunk.page_number,
                Chunk.content,
                Document.filename,
                distance,
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Document.user_id == user_id,
                Document.status == DocumentStatus.COMPLETED,
            )
            .order_by(distance)
            .limit(top_k)
        )
        if document_ids:
            statement = statement.where(Chunk.document_id.in_(document_ids))

        return self.db.execute(statement).all()
