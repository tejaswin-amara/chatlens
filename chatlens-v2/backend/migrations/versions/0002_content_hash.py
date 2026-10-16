"""Bridge 001_content_hash.sql.

Revision ID: 0002_content_hash
Revises: 0001_initial_schema
Create Date: 2026-10-16 16:05:00.000000

"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0002_content_hash"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ctx = op.get_context()
    is_postgres = ctx.dialect.name == "postgresql"

    if is_postgres:
        sql_path = Path(__file__).resolve().parent.parent / "001_content_hash.sql"
        if sql_path.exists():
            sql_content = sql_path.read_text(encoding="utf-8")
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    op.execute(stmt)
        else:
            op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS content_hash TEXT;")
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_messages_content_hash ON messages (content_hash);"
            )
    else:
        try:
            op.execute("ALTER TABLE messages ADD COLUMN content_hash TEXT;")
        except Exception:
            pass
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_messages_content_hash ON messages (content_hash);"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_messages_content_hash;")
    ctx = op.get_context()
    if ctx.dialect.name == "postgresql":
        op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS content_hash;")
