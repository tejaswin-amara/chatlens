import json
import time
import urllib.parse
import urllib.request

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

class BotClient:
    def __init__(self, token: str | None = None):
        self.token = token or settings.bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    def _request(self, endpoint: str, data: dict | None = None, timeout: int = 30) -> dict:
        if not self.base_url:
            raise ValueError("BOT_TOKEN is not set")

        url = f"{self.base_url}/{endpoint}"
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')

        payload = json.dumps(data).encode('utf-8') if data else None

        try:
            with urllib.request.urlopen(req, data=payload, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                err_data = json.loads(e.read().decode())
                retry_after = err_data.get('parameters', {}).get('retry_after', 1)
                raise Exception(f"429:{retry_after}")
            if e.code == 409:
                raise Exception("409:Conflict")
            raise Exception(f"Telegram Bot HTTPError {e.code}: {e.read().decode()}")

    def send(self, text: str, buttons: list | None = None) -> dict:
        data: dict = {
            "chat_id": settings.owner_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if buttons:
            data["reply_markup"] = {"inline_keyboard": [buttons]}

        try:
            return self._request("sendMessage", data)
        except Exception as e:
            err = str(e)
            if err.startswith("429:"):
                time.sleep(int(err.split(":")[1]))
                return self._request("sendMessage", data)
            raise

    def edit(self, message_id: int | str, text: str) -> dict:
        data = {
            "chat_id": settings.owner_chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            return self._request("editMessageText", data)
        except Exception as e:
            err = str(e)
            if err.startswith("429:"):
                time.sleep(int(err.split(":")[1]))
                return self._request("editMessageText", data)
            raise

    def answer_callback(self, callback_id: str | None) -> dict:
        data = {"callback_query_id": callback_id or ""}
        try:
            return self._request("answerCallbackQuery", data)
        except Exception as e:
            err = str(e)
            if err.startswith("429:"):
                time.sleep(int(err.split(":")[1]))
                return self._request("answerCallbackQuery", data)
            raise

    def get_updates(self, offset: int, timeout: int = 30) -> dict:
        data = {"offset": offset, "timeout": timeout}
        try:
            return self._request("getUpdates", data, timeout=timeout + 5)
        except Exception as e:
            err = str(e)
            if err.startswith("429:"):
                time.sleep(int(err.split(":")[1]))
                return self._request("getUpdates", data, timeout=timeout + 5)
            if err.startswith("409:"):
                logger.warning("Bot 409 Conflict. Another instance is running.")
                time.sleep(5)
                return {"ok": True, "result": []}
            raise

bot = BotClient()
