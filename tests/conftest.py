import shutil
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from src.config import settings
from src.governance.audit import audit_logger
from src.notify.bot import bot
from src.utils import clock
from src.utils.deduplication import deduplicator


@pytest.fixture(scope="session", autouse=True)
def ensure_frontend_out_fixture():
    """Ensure frontend/out has minimal static structure so E2E tests pass if not pre-built."""
    out_dir = Path("chatlens-v2/frontend/out")
    created = False
    if not out_dir.exists():
        created = True
        static_dir = out_dir / "_next" / "static" / "chunks"
        static_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            "<!doctype html><html><head><title>ChatLens</title></head>"
            "<body><div id=\"root\">ChatLens</div></body></html>",
            encoding="utf-8",
        )
        (static_dir / "main.js").write_text("console.log('chatlens');", encoding="utf-8")
        (static_dir / "main.css").write_text("body { margin: 0; }", encoding="utf-8")
    yield
    if created and out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def isolate_spark_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure every test runs with an isolated temporary SQLite database and offline defaults."""
    db_file = str(tmp_path / "spark_test.db")
    monkeypatch.setattr(settings, "spark_db", db_file)
    monkeypatch.setenv("SPARK_DB", db_file)
    deduplicator.db_path = db_file
    deduplicator._ensure_db()
    audit_logger.db_path = db_file
    audit_logger._ensure_schema()

    if not settings.owner_chat_id:
        monkeypatch.setattr(settings, "owner_chat_id", 12345678)
    if not settings.bot_token:
        monkeypatch.setattr(settings, "bot_token", SecretStr("bot123:mock_test_token"))
    if not bot.token:
        bot.token = "bot123:mock_test_token"
        bot.base_url = "https://api.telegram.org/botbot123:mock_test_token"

    yield
    deduplicator.db_path = None
    audit_logger.db_path = None


@pytest.fixture
def frozen_clock(monkeypatch):
    def _freeze(iso: str):
        fixed = datetime.fromisoformat(iso)
        monkeypatch.setattr(clock, "now_ist", lambda: fixed.astimezone(clock.IST))

    return _freeze
