import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingestion.handlers import catch_up_chats
from src.utils.deduplication import deduplicator


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Need to simulate async behavior
    client.get_messages = AsyncMock()
    return client


@pytest.fixture
def clean_db():
    deduplicator._init_db()
    with deduplicator._get_conn() as conn:
        conn.execute("DELETE FROM chat_state")
        conn.execute("DELETE FROM seen")


@pytest.mark.asyncio
async def test_catch_up_first_run(mock_client, clean_db):
    # Empty chat baseline: returns empty
    mock_client.get_messages.return_value = []

    with patch("src.config.settings.spark_chat_ids", "123"):
        await catch_up_chats(mock_client)

    assert deduplicator.get_chat_state(123) is None


@pytest.mark.asyncio
async def test_catch_up_inaccessible_chat(mock_client, clean_db):
    mock_client.get_messages.side_effect = Exception("Forbidden")
    with patch("src.config.settings.spark_chat_ids", "123"):
        await catch_up_chats(mock_client)
    assert deduplicator.get_chat_state(123) is None


@pytest.mark.asyncio
async def test_catch_up_live_message_advances(mock_client, clean_db):
    msg1 = MagicMock()
    msg1.id = 100
    msg1.date = datetime.datetime.now(datetime.UTC)
    msg1.out = False
    msg1.text = "Hello"

    msg2 = MagicMock()
    msg2.id = 101
    msg2.date = datetime.datetime.now(datetime.UTC)
    msg2.out = False
    msg2.text = "World"

    mock_client.get_messages.side_effect = [[msg2], [msg1, msg2]]

    with patch("src.config.settings.spark_chat_ids", "123"):
        await catch_up_chats(mock_client)
        assert deduplicator.get_chat_state(123) == 101


@pytest.mark.asyncio
async def test_catch_up_processes_backlog(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)

    msg = MagicMock()
    msg.id = 60
    msg.date = datetime.datetime.now(datetime.UTC)
    msg.out = False
    msg.text = "Process me"
    msg.voice = None
    msg.photo = None
    msg.document = None
    msg.get_chat = AsyncMock()
    msg.get_sender = AsyncMock()

    mock_client.get_messages.return_value = [msg]

    with patch("src.config.settings.spark_chat_ids", "123"):
        with patch("src.ingestion.handlers.process_message") as mock_process:
            await catch_up_chats(mock_client)
            mock_process.assert_called_once()
            assert deduplicator.get_chat_state(123) == 60


@pytest.mark.asyncio
async def test_catch_up_outgoing_skipped(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)

    msg = MagicMock()
    msg.id = 60
    msg.date = datetime.datetime.now(datetime.UTC)
    msg.out = True  # Outgoing
    msg.text = "Skip me"

    mock_client.get_messages.return_value = [msg]

    with patch("src.config.settings.spark_chat_ids", "123"):
        with patch("src.ingestion.handlers.process_message") as mock_process:
            await catch_up_chats(mock_client)
            mock_process.assert_not_called()
            assert deduplicator.get_chat_state(123) == 60


@pytest.mark.asyncio
async def test_catch_up_7_day_cutoff(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)

    msg = MagicMock()
    msg.id = 60
    # 8 days ago
    msg.date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=8)
    msg.out = False

    mock_client.get_messages.return_value = [msg]

    with patch("src.config.settings.spark_chat_ids", "123"):
        with patch("src.ingestion.handlers.process_message") as mock_process:
            await catch_up_chats(mock_client)
            mock_process.assert_not_called()
            assert deduplicator.get_chat_state(123) == 60


@pytest.mark.asyncio
async def test_catch_up_truncation_warning(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)

    msgs = [MagicMock(id=i, date=datetime.datetime.now(datetime.UTC), out=True) for i in range(200)]
    mock_client.get_messages.return_value = msgs

    with patch("src.config.settings.spark_chat_ids", "123"):
        with patch("src.ingestion.handlers.logger.warning") as mock_warn:
            await catch_up_chats(mock_client)
            mock_warn.assert_called_with("Catch-up truncated at 200 messages", chat_id=123)


@pytest.mark.asyncio
async def test_catch_up_runs_after_reconnect(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)
    mock_client.get_messages.return_value = []

    with patch("src.config.settings.spark_chat_ids", "123"):
        await catch_up_chats(mock_client)
        assert deduplicator.get_chat_state(123) == 50


@pytest.mark.asyncio
async def test_catch_up_max_keeping_upsert(mock_client, clean_db):
    deduplicator.update_chat_state(123, 50)
    deduplicator.update_chat_state(123, 60)
    assert deduplicator.get_chat_state(123) == 60
