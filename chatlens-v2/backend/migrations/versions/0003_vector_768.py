"""Bridge 002_vector_768.sql.

Revision ID: 0003_vector_768
Revises: 0002_content_hash
Create Date: 2026-10-16 16:10:00.000000

"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0003_vector_768"
down_revision: Union[str, None] = "0002_content_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ctx = op.get_context()
    is_postgres = ctx.dialect.name == "postgresql"

    if is_postgres:
        sql_path = Path(__file__).resolve().parent.parent / "002_vector_768.sql"
        if sql_path.exists():
            sql_content = sql_path.read_text(encoding="utf-8")
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    op.execute(stmt)
        else:
            op.execute("ALTER TABLE messages ALTER COLUMN embedding TYPE vector(768);")
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages USING hnsw (embedding vector_cosine_ops);"
            )


def downgrade() -> None:
    ctx = op.get_context()
    if ctx.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_messages_embedding;")
