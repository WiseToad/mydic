"""wordbook_entries unique word per user

Revision ID: a3e1f9b72c04
Revises: fb63d502c17f
Create Date: 2026-05-26 10:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a3e1f9b72c04'
down_revision: Union[str, Sequence[str], None] = 'fb63d502c17f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate rows, keeping the one with the lowest id in each
    # (user_id, source_lang, target_lang, source_text) group.
    op.execute("""
        DELETE FROM wordbook_entries
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM wordbook_entries
            GROUP BY user_id, source_lang, target_lang, source_text
        )
    """)

    op.create_unique_constraint(
        'uq_wordbook_entries_user_word',
        'wordbook_entries',
        ['user_id', 'source_lang', 'target_lang', 'source_text'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_wordbook_entries_user_word',
        'wordbook_entries',
        type_='unique',
    )
