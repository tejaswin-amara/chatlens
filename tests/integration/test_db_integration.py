"""Integration tests for PostgreSQL + pgvector and content_hash deduplication."""

import shutil
import subprocess

import pytest

try:
    import psycopg

    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


def _docker_available() -> bool:
    docker_bin = shutil.which("docker")
    if not TESTCONTAINERS_AVAILABLE or not docker_bin:
        return False
    try:
        res = subprocess.run(  # noqa: S603
            [docker_bin, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


@pytest.mark.integration
def test_postgres_pgvector_content_hash() -> None:
    if not _docker_available():
        pytest.skip("Docker daemon not running; skipping integration test")

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        raw_url = postgres.get_connection_url()
        conn_url = raw_url.replace("postgresql+psycopg2://", "postgresql://")
        with psycopg.connect(conn_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Enable vector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # Create messages table
                cur.execute("""
                    CREATE TABLE messages (
                        id SERIAL PRIMARY KEY,
                        platform VARCHAR,
                        chat_name VARCHAR,
                        sender VARCHAR,
                        timestamp VARCHAR,
                        text TEXT,
                        reply_to VARCHAR,
                        forwarded_from VARCHAR,
                        embedding vector(1536),
                        content_hash VARCHAR UNIQUE
                    );
                """)

                insert_sql = """
                    INSERT INTO messages (
                        platform, chat_name, sender, timestamp, text, content_hash
                    )
                    VALUES ('telegram', 'CSE_General', 'Alice', '2026-10-15', 'Hello', 'hash_123')
                    ON CONFLICT (content_hash) DO NOTHING
                    RETURNING id;
                """

                # Insert initial message
                cur.execute(insert_sql)
                row = cur.fetchone()
                assert row is not None

                # Attempt duplicate insert with same content_hash
                cur.execute(insert_sql)
                dup_row = cur.fetchone()
                assert dup_row is None, "Duplicate content_hash should have been ignored"

                # Verify single row exists
                cur.execute("SELECT COUNT(*) FROM messages;")
                assert cur.fetchone()[0] == 1
