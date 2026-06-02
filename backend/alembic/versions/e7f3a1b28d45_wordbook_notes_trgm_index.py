"""wordbook notes: GIN trigram index for search

Revision ID: e7f3a1b28d45
Revises: c4d2e8f91b37
Create Date: 2026-06-02 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = 'e7f3a1b28d45'
down_revision: Union[str, Sequence[str], None] = 'c4d2e8f91b37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # immutable_unaccent() and pg_trgm are already available from the
    # c4d2e8f91b37 migration.  A partial index (WHERE notes IS NOT NULL)
    # keeps the index compact and matches the query predicate: similarity()
    # on a NULL operand evaluates to NULL which is never > threshold.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_wordbook_entries_notes_trgm
        ON wordbook_entries
        USING GIN (immutable_unaccent(lower(notes)) gin_trgm_ops)
        WHERE notes IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wordbook_entries_notes_trgm")
