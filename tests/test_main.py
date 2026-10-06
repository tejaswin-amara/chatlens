from unittest.mock import MagicMock, patch

import pytest
from telethon.errors import AuthKeyUnregisteredError

from src.main import run_daemon


@pytest.mark.asyncio
async def test_daemon_exit_codes_config_failure():
    with patch("src.main.settings") as mock_settings:
        mock_settings.validate_required.side_effect = ValueError("fake config error")
        code = await run_daemon(handle_signals=False)
        assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_unauthorized():
    with patch("src.main.settings"):
        with patch("src.main.create_telegram_client") as mock_create:
            mock_client = MagicMock()
            from unittest.mock import AsyncMock

            mock_client.connect = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=False)
            mock_create.return_value = mock_client

            code = await run_daemon(handle_signals=False)
            assert code == 2


@pytest.mark.asyncio
async def test_daemon_exit_codes_auth_error_mid_run():
    with patch("src.main.settings"):
        with patch("src.main.create_telegram_client") as mock_create:
            mock_client = MagicMock()
            from unittest.mock import AsyncMock

            mock_client.connect = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=True)

            async def fake_run():
                raise AuthKeyUnregisteredError(request=None)

            mock_client.run_until_disconnected = fake_run
            mock_create.return_value = mock_client

            code = await run_daemon(handle_signals=False)
            assert code == 2
