"""baseline existing schema

Revision ID: 0d10f4385c8d
Revises: 
Create Date: 2026-10-14 11:44:51.048819

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0d10f4385c8d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Creates the original schema (formerly only in infra/init.sql) so an empty
    database can be built from migrations alone. IF NOT EXISTS keeps it a
    no-op for databases that were initialised by init.sql.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY,
            filename TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id BIGSERIAL PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id)")


def downgrade() -> None:
    """Downgrade schema."""
    pass
