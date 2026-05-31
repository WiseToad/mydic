"""wordbook search: pg_trgm, unaccent, GIN trigram indexes

Revision ID: c4d2e8f91b37
Revises: d4a5b6c7e8f9
Create Date: 2026-05-31 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = 'c4d2e8f91b37'
down_revision: Union[str, Sequence[str], None] = 'd4a5b6c7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions required for fuzzy trigram search with accent-folding.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # unaccent() is VOLATILE by default and therefore cannot appear in a
    # functional index definition.  Wrapping it in an IMMUTABLE SQL function
    # is the standard workaround.
    op.execute("""
        CREATE OR REPLACE FUNCTION immutable_unaccent(text)
        RETURNS text AS $$
        BEGIN
            RETURN public.unaccent($1);
        END;
        $$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE STRICT
        SET search_path = public
    """)

    # GIN trigram indexes on the accent-folded, lower-cased search columns.
    # These enable efficient similarity searches via the % operator and also
    # help the planner when using similarity() with a low enough threshold.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_wordbook_entries_source_text_trgm
        ON wordbook_entries
        USING GIN (immutable_unaccent(lower(source_text)) gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_wordbook_entries_target_text_trgm
        ON wordbook_entries
        USING GIN (immutable_unaccent(lower(target_text)) gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wordbook_entries_target_text_trgm")
    op.execute("DROP INDEX IF EXISTS ix_wordbook_entries_source_text_trgm")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
