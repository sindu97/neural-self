"""add HNSW index on chunk embeddings

Built CONCURRENTLY so uploads and searches keep working while the index is
created; that cannot run inside a transaction, hence the autocommit block.
If a concurrent build is interrupted it leaves an INVALID index behind;
the DROP ... IF EXISTS on retry cleans that up.

Revision ID: f9b2d6e3c1a8
Revises: e4c8f1a2b7d9
Create Date: 2026-10-15 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f9b2d6e3c1a8'
down_revision: Union[str, Sequence[str], None] = 'e4c8f1a2b7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_chunks_embedding_hnsw")
        op.execute(
            "CREATE INDEX CONCURRENTLY ix_chunks_embedding_hnsw ON chunks "
            "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_chunks_embedding_hnsw")
