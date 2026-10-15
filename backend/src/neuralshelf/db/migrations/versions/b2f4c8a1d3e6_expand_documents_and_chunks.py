"""expand documents, chunks, users and refresh tokens

Adds document ownership and ingestion status, chunk ordering and metadata,
user updated_at, and refresh-token rotation links. Purely additive: existing
rows are kept and backfilled.

Revision ID: b2f4c8a1d3e6
Revises: 7c3a91d2e4b5
Create Date: 2026-10-15 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2f4c8a1d3e6'
down_revision: Union[str, Sequence[str], None] = '7c3a91d2e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # users
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # refresh_tokens
    op.add_column('refresh_tokens', sa.Column('replaced_by_token_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_refresh_tokens_replaced_by_token_id', 'refresh_tokens', 'refresh_tokens',
        ['replaced_by_token_id'], ['id'], ondelete='SET NULL',
    )
    # The composite index also serves lookups by user_id alone.
    op.create_index(
        'ix_refresh_tokens_user_id_expires_at', 'refresh_tokens', ['user_id', 'expires_at'],
    )
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')

    # documents
    op.add_column('documents', sa.Column('user_id', sa.UUID(), nullable=True))
    conn = op.get_bind()
    orphaned = conn.execute(sa.text('SELECT count(*) FROM documents WHERE user_id IS NULL')).scalar()
    if orphaned:
        raise RuntimeError(
            f'{orphaned} existing document(s) have no owner. Assign documents.user_id '
            'for these rows (or remove them deliberately) before running this migration.'
        )
    op.alter_column('documents', 'user_id', nullable=False)
    op.create_foreign_key(
        'fk_documents_user_id_users', 'documents', 'users', ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.add_column('documents', sa.Column('storage_key', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('content_type', sa.String(length=150), nullable=True))
    op.add_column('documents', sa.Column('file_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column(
        'documents',
        sa.Column('status', sa.String(length=30), server_default='uploaded', nullable=False),
    )
    op.add_column('documents', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        'ck_documents_status', 'documents',
        "status IN ('uploaded', 'processing', 'completed', 'failed')",
    )
    op.create_check_constraint(
        'ck_documents_file_size_non_negative', 'documents',
        'file_size_bytes IS NULL OR file_size_bytes >= 0',
    )
    op.create_index(
        'ix_documents_user_id_created_at', 'documents', ['user_id', sa.text('created_at DESC')],
    )
    op.create_index('ix_documents_user_id_status', 'documents', ['user_id', 'status'])

    # chunks
    op.add_column('chunks', sa.Column('chunk_index', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE chunks AS c
        SET chunk_index = ordered.idx
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY document_id ORDER BY page_number, id
            ) - 1 AS idx
            FROM chunks
        ) AS ordered
        WHERE c.id = ordered.id
        """
    )
    op.alter_column('chunks', 'chunk_index', nullable=False)
    op.alter_column('chunks', 'page_number', existing_type=sa.Integer(), nullable=True)
    op.add_column(
        'chunks', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_unique_constraint(
        'uq_chunks_document_id_chunk_index', 'chunks', ['document_id', 'chunk_index'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_chunks_document_id_chunk_index', 'chunks', type_='unique')
    op.drop_column('chunks', 'metadata')
    op.alter_column('chunks', 'page_number', existing_type=sa.Integer(), nullable=False)
    op.drop_column('chunks', 'chunk_index')

    op.drop_index('ix_documents_user_id_status', table_name='documents')
    op.drop_index('ix_documents_user_id_created_at', table_name='documents')
    op.drop_constraint('ck_documents_file_size_non_negative', 'documents', type_='check')
    op.drop_constraint('ck_documents_status', 'documents', type_='check')
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'error_message')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'file_size_bytes')
    op.drop_column('documents', 'content_type')
    op.drop_column('documents', 'storage_key')
    op.drop_constraint('fk_documents_user_id_users', 'documents', type_='foreignkey')
    op.drop_column('documents', 'user_id')

    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'])
    op.drop_index('ix_refresh_tokens_user_id_expires_at', table_name='refresh_tokens')
    op.drop_constraint(
        'fk_refresh_tokens_replaced_by_token_id', 'refresh_tokens', type_='foreignkey',
    )
    op.drop_column('refresh_tokens', 'replaced_by_token_id')

    op.drop_column('users', 'updated_at')
