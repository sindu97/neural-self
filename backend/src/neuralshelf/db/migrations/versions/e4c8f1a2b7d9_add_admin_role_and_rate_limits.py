"""add admin role and rate limit buckets

Revision ID: e4c8f1a2b7d9
Revises: d7a3b9c1e5f2
Create Date: 2026-10-15 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4c8f1a2b7d9'
down_revision: Union[str, Sequence[str], None] = 'd7a3b9c1e5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False),
    )
    op.create_table('rate_limit_buckets',
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key', 'window_start')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('rate_limit_buckets')
    op.drop_column('users', 'is_admin')
