"""Initial messages table schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-16 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ctx = op.get_context()
    is_postgres = ctx.dialect.name == "postgresql"

    if is_postgres:
        op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            platform VARCHAR,
            chat_name VARCHAR,
            sender VARCHAR,
            timestamp VARCHAR,
            text TEXT,
            reply_to VARCHAR,
            forwarded_from VARCHAR,
            embedding vector(768)
        );
        """)
    else:
        op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform VARCHAR,
            chat_name VARCHAR,
            sender VARCHAR,
            timestamp VARCHAR,
            text TEXT,
            reply_to VARCHAR,
            forwarded_from VARCHAR,
            embedding TEXT
        );
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_id ON messages (id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_name ON messages (chat_name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON messages (chat_name, timestamp);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messages;")
