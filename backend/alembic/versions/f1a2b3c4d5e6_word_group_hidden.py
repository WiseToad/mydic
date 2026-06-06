"""add hidden flag to word_groups

Revision ID: f1a2b3c4d5e6
Revises: e7f3a1b28d45
Create Date: 2026-06-05 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e7f3a1b28d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'word_groups',
        sa.Column('hidden', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('word_groups', 'hidden')
