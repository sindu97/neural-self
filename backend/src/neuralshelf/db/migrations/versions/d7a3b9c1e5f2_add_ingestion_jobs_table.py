"""add ingestion jobs table

Durable job queue for document ingestion, processed by the worker service.
Documents still waiting or mid-processing get a queued job so the worker
picks them up.

Revision ID: d7a3b9c1e5f2
Revises: c5d9e2f7a8b4
Create Date: 2026-10-15 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd7a3b9c1e5f2'
down_revision: Union[str, Sequence[str], None] = 'c5d9e2f7a8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ingestion_jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='queued', nullable=False),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('available_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('locked_by', sa.String(length=200), nullable=True),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint(
        "status IN ('queued', 'running', 'succeeded', 'failed')", name='ck_ingestion_jobs_status',
    ),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_ingestion_jobs_status_available_at', 'ingestion_jobs', ['status', 'available_at'],
    )
    op.create_index(
        'uq_ingestion_jobs_active_document', 'ingestion_jobs', ['document_id'],
        unique=True, postgresql_where=sa.text("status IN ('queued', 'running')"),
    )

    op.execute(
        """
        INSERT INTO ingestion_jobs (id, document_id, max_attempts)
        SELECT gen_random_uuid(), id, 5
        FROM documents
        WHERE status IN ('uploaded', 'processing')
        """
    )
    op.execute("UPDATE documents SET status = 'uploaded' WHERE status = 'processing'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_ingestion_jobs_active_document', table_name='ingestion_jobs')
    op.drop_index('ix_ingestion_jobs_status_available_at', table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
