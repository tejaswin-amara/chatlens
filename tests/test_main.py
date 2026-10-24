import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.errors import (
    AuthKeyUnregisteredError,
    FloodWaitError,
    SessionExpiredError,
    SessionRevokedError,
    UserDeactivatedBanError,
    UserDeactivatedError,
)

from src.main import bot_callback_poll, run_daemon, run_heartbeat


async def guard(coro, seconds: float = 5.0):
    return await asyncio.wait_for(coro, timeout=seconds)


class FakeTelegramClient:
    def __init__(self, authorized: bool = True):
        self.connected = False
        self.authorized = authorized
        self.disconnected = False
        self.disconnect_awaited = False
        self.connect_calls = 0
        self.handlers: list = []
        self._disconnect_event = asyncio.Event()

    async def connect(self):
        self.connect_calls += 1
        self.connected = True

    def is_connected(self) -> bool:
        return self.connected and not self.disconnected

    async def is_user_authorized(self) -> bool:
        return self.authorized

    async def get_messages(self, *args, **kwargs):
        return []

    async def run_until_disconnected(self):
        await self._disconnect_event.wait()

    async def disconnect(self):
        self.disconnected = True
        self.disconnect_awaited = True
        self._disconnect_event.set()

    def on(self, event):
        def decorator(f):
            self.handlers.append((event, f))
            return f

        return decorator


@pytest.fixture(autouse=True)
def mock_valid_settings():
    with patch("src.main.settings") as s:
        s.telegram_api_id = 123
        s.telegram_api_hash = MagicMock(get_secret_value=lambda: "hash")
        s.telegram_session_string = MagicMock(get_secret_value=lambda: "session")
        s.google_credentials_base64 = MagicMock(get_secret_value=lambda: "b64")
        s.gemini_api_key = MagicMock(get_secret_value=lambda: "key")
        s.spark_mode = "dry"
        s.allowed_chat_ids = [100]
        s.bot_token = MagicMock(get_secret_value=lambda: "token")
        s.owner_chat_id = 12345
        s.validate_required = MagicMock()
        yield s


@pytest.mark.asyncio
async def test_daemon_clean_shutdown():
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()

    async def _trigger():
        await asyncio.sleep(0.02)
        stop_event.set()

    asyncio.create_task(_trigger())
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        assert client.disconnect_awaited is True


@pytest.mark.asyncio
async def test_daemon_exit_codes_config_failure(mock_valid_settings):
    mock_valid_settings.validate_required.side_effect = ValueError("fake config error")
    code = await guard(run_daemon(handle_signals=False))
    assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_unauthorized():
    client = FakeTelegramClient(authorized=False)
    stop_event = asyncio.Event()
    code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
    assert code == 2
    assert client.disconnect_awaited is True


@pytest.mark.asyncio
async def test_daemon_exit_codes_auth_key_unregistered():
    client = FakeTelegramClient(authorized=True)
    client.run_until_disconnected = AsyncMock(  # type: ignore[method-assign]
        side_effect=AuthKeyUnregisteredError(request=None)
    )
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(
            run_daemon(client=client, stop_event=asyncio.Event(), handle_signals=False)
        )
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_session_revoked():
    client = FakeTelegramClient(authorized=True)
    client.run_until_disconnected = AsyncMock(  # type: ignore[method-assign]
        side_effect=SessionRevokedError(request=None)
    )
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(
            run_daemon(client=client, stop_event=asyncio.Event(), handle_signals=False)
        )
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_session_expired():
    client = FakeTelegramClient(authorized=True)
    client.run_until_disconnected = AsyncMock(  # type: ignore[method-assign]
        side_effect=SessionExpiredError(request=None)
    )
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(
            run_daemon(client=client, stop_event=asyncio.Event(), handle_signals=False)
        )
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_user_deactivated():
    client = FakeTelegramClient(authorized=True)
    client.run_until_disconnected = AsyncMock(  # type: ignore[method-assign]
        side_effect=UserDeactivatedError(request=None)
    )
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(
            run_daemon(client=client, stop_event=asyncio.Event(), handle_signals=False)
        )
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_user_deactivated_ban():
    client = FakeTelegramClient(authorized=True)
    client.run_until_disconnected = AsyncMock(  # type: ignore[method-assign]
        side_effect=UserDeactivatedBanError(request=None)
    )
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(
            run_daemon(client=client, stop_event=asyncio.Event(), handle_signals=False)
        )
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_flood_wait_handling():
    client = FakeTelegramClient(authorized=True)
    flood = FloodWaitError(request=None)
    flood.seconds = 0
    stop_event = asyncio.Event()

    async def _fail_then_stop():
        client.connect_calls += 1
        if client.connect_calls == 1:
            raise flood
        stop_event.set()

    client.connect = _fail_then_stop  # type: ignore[method-assign]

    with patch("src.main._sleep_or_stop", new_callable=AsyncMock) as mock_sleep:
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_sleep.assert_awaited()


@pytest.mark.asyncio
async def test_daemon_startup_notification_loaded(mock_valid_settings):
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    mock_tt = MagicMock(path="data/timetable_T04.toml", sample=False)
    with (
        patch("src.timetable.load", return_value=mock_tt),
        patch("src.notify.bot.bot.send") as mock_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.deduplication.deduplicator.meta_get", return_value=None),
    ):
        mock_valid_settings.spark_mode = "live"
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_send.assert_called_once()
        assert "timetable loaded" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_daemon_startup_notification_sample(mock_valid_settings):
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    mock_tt = MagicMock(path="data/timetable_T04.toml", sample=True)
    with (
        patch("src.timetable.load", return_value=mock_tt),
        patch("src.notify.bot.bot.send") as mock_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.deduplication.deduplicator.meta_get", return_value=None),
    ):
        mock_valid_settings.spark_mode = "live"
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_send.assert_called_once()
        assert "timetable missing/sample" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_bot_callback_poll_undo_routing(mock_valid_settings):
    with (
        patch("src.notify.bot.bot.get_updates") as mock_updates,
        patch("src.ingestion.handlers.handle_undo_command", new_callable=AsyncMock) as mock_undo,
    ):
        mock_valid_settings.spark_mode = "live"
        mock_updates.side_effect = [
            {
                "result": [
                    {"update_id": 1, "message": {"text": "/undo", "from": {"id": 99999}}},
                    {
                        "update_id": 2,
                        "message": {"text": "/undo now", "from": {"id": 12345}},
                    },
                ]
            },
            asyncio.CancelledError(),
        ]
        with pytest.raises(asyncio.CancelledError):
            await guard(bot_callback_poll())

        mock_undo.assert_called_once()
        assert mock_undo.call_args[0][0]["text"] == "/undo now"


@pytest.mark.asyncio
async def test_bot_callback_poll_no_token_returns_immediately(mock_valid_settings):
    with patch("src.notify.bot.bot.get_updates") as mock_get:
        mock_valid_settings.bot_token = None
        await guard(bot_callback_poll())
        mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_bot_callback_poll_runs_in_dry_mode(mock_valid_settings):
    with (
        patch("src.notify.bot.bot.delete_webhook") as mock_del_wh,
        patch("src.notify.bot.bot.set_my_commands") as mock_set_cmds,
        patch("src.notify.bot.bot.get_updates") as mock_get,
        patch("src.ingestion.handlers.handle_bot_command", new_callable=AsyncMock) as mock_cmd,
    ):
        mock_valid_settings.spark_mode = "dry"
        mock_get.side_effect = [
            {
                "result": [
                    {
                        "update_id": 1,
                        "message": {"text": "/today", "from": {"id": 12345}},
                    }
                ]
            },
            asyncio.CancelledError(),
        ]
        with pytest.raises(asyncio.CancelledError):
            await guard(bot_callback_poll())

        mock_del_wh.assert_called_once()
        mock_set_cmds.assert_called_once()
        assert mock_get.call_count == 2
        mock_cmd.assert_called_once()
        assert mock_cmd.call_args[0][0]["text"] == "/today"


@pytest.mark.asyncio
async def test_daemon_startup_debounce(mock_valid_settings):
    import time

    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    with (
        patch("src.notify.bot.bot.send") as mock_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.deduplication.deduplicator.meta_get", return_value=str(time.time())),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_heartbeat_logs_immediately():
    with (
        patch("src.workspace.sheets_logger.sheets_logger.log_heartbeat") as mock_hb,
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_heartbeat())
        mock_hb.assert_called_once()


@pytest.mark.asyncio
async def test_daemon_clean_client_disconnect():
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)
    with patch("src.main.catch_up_chats", new=AsyncMock()):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        assert client.disconnect_awaited is True


@pytest.mark.asyncio
async def test_run_reminders_dispatches_due_items(mock_valid_settings):
    from src.main import run_reminders
    from src.utils import clock

    fake_item = {
        "id": 99,
        "event": {
            "course_name": "Test Course",
            "course_code": "TC101",
            "period": "10:00 - 11:00",
            "summary": "Midterm Exam",
            "target_date": clock.today_ist().strftime("%Y-%m-%d"),
            "intent": "EXAM_DEADLINE",
        },
        "status": "PENDING",
    }
    with (
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[fake_item]),
        patch("src.utils.deduplication.deduplicator.meta_get", return_value=None),
        patch("src.utils.deduplication.deduplicator.meta_set") as mock_set,
        patch("src.notify.bot.bot.send") as mock_send,
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_reminders())

        mock_send.assert_called_once()
        assert "Test Course" in mock_send.call_args[0][0]
        assert "Midterm Exam" in mock_send.call_args[0][0]
        mock_set.assert_called_once()


@pytest.mark.asyncio
async def test_run_reminders_debounces_already_reminded(mock_valid_settings):
    from src.main import run_reminders
    from src.utils import clock

    fake_item = {
        "id": 99,
        "event": {
            "course_name": "Test Course",
            "summary": "Midterm Exam",
            "target_date": clock.today_ist().strftime("%Y-%m-%d"),
        },
        "status": "PENDING",
    }
    with (
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[fake_item]),
        patch("src.utils.deduplication.deduplicator.meta_get", return_value="1792850000"),
        patch("src.notify.bot.bot.send") as mock_send,
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_reminders())

        mock_send.assert_not_called()

