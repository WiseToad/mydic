"""wordbook group_id mandatory with cascade delete

Revision ID: d4a5b6c7e8f9
Revises: a3e1f9b72c04
Create Date: 2026-05-28 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4a5b6c7e8f9'
down_revision: Union[str, Sequence[str], None] = 'a3e1f9b72c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create a "Default" group for every user who has orphaned entries
    # (group_id IS NULL), but only if that user does not already have a group
    # named "Default".
    op.execute("""
        INSERT INTO word_groups (user_id, name, position)
        SELECT DISTINCT we.user_id, 'Default', 0
        FROM wordbook_entries we
        WHERE we.group_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM word_groups wg
              WHERE wg.user_id = we.user_id
                AND wg.name = 'Default'
          )
    """)

    # Step 2: Assign all orphaned entries to their user's lowest-id group
    # named "Default" (just created above, or pre-existing).
    op.execute("""
        UPDATE wordbook_entries
        SET group_id = (
            SELECT id FROM word_groups
            WHERE user_id = wordbook_entries.user_id
              AND name = 'Default'
            ORDER BY id
            LIMIT 1
        )
        WHERE group_id IS NULL
    """)

    # Step 3: Drop the existing FK constraint (ON DELETE SET NULL).
    # PostgreSQL auto-names unnamed FK constraints as <table>_<column>_fkey.
    op.drop_constraint(
        'wordbook_entries_group_id_fkey',
        'wordbook_entries',
        type_='foreignkey',
    )

    # Step 4: Make group_id NOT NULL (all NULLs are gone after step 2).
    op.alter_column('wordbook_entries', 'group_id', nullable=False)

    # Step 5: Re-create the FK with ON DELETE CASCADE.
    op.create_foreign_key(
        'wordbook_entries_group_id_fkey',
        'wordbook_entries', 'word_groups',
        ['group_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'wordbook_entries_group_id_fkey',
        'wordbook_entries',
        type_='foreignkey',
    )
    op.alter_column('wordbook_entries', 'group_id', nullable=True)
    op.create_foreign_key(
        'wordbook_entries_group_id_fkey',
        'wordbook_entries', 'word_groups',
        ['group_id'], ['id'],
        ondelete='SET NULL',
    )
