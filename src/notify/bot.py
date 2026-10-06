import json
import time

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BotRateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"429:{retry_after}")


class BotConflict(Exception):
    def __init__(self):
        super().__init__("409:Conflict")


class BotError(Exception):
    pass


class BotClient:
    def __init__(self, token=None):
        raw_token = token or settings.bot_token
        self.token = (
            raw_token.get_secret_value() if hasattr(raw_token, "get_secret_value") else raw_token
        )
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    def _request(self, endpoint: str, data: dict | None = None, timeout: int = 30) -> dict:
        if not self.base_url:
            raise ValueError("BOT_TOKEN is not set")

        url = f"{self.base_url}/{endpoint}"
        import urllib.error

        req = urllib.request.Request(url)
        req.add_header("Content-Type", "application/json")

        payload = json.dumps(data).encode("utf-8") if data else None

        try:
            with urllib.request.urlopen(req, data=payload, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                err_data = json.loads(e.read().decode())
                retry_after = min(err_data.get("parameters", {}).get("retry_after", 1), 60)
                raise BotRateLimited(retry_after)
            if e.code == 409:
                raise BotConflict()
            raise BotError(f"Telegram Bot HTTPError {e.code}: {e.read().decode()}")

    def _retry(self, endpoint: str, data: dict, timeout: int = 30):
        for attempt in range(2):
            try:
                return self._request(endpoint, data, timeout)
            except BotRateLimited as e:
                import time

                time.sleep(e.retry_after)
            except BotError as e:
                import re
                import time

                if "HTTPError" in str(e):
                    code_str = re.search(r"HTTPError (\d+):", str(e))
                    if code_str and int(code_str.group(1)) < 500:
                        raise e
                time.sleep(2**attempt)
            except Exception:
                import time

                time.sleep(2**attempt)
        return self._request(endpoint, data, timeout)

    def send(self, text: str, buttons: list | None = None, parse_mode: str | None = None) -> dict:
        data: dict = {"chat_id": settings.owner_chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        elif "**" in text or "`" in text or "*" in text:
            data["parse_mode"] = "Markdown"

        if buttons:
            data["reply_markup"] = {"inline_keyboard": [buttons]}

        return self._retry("sendMessage", data)

    def edit(self, message_id: int | str, text: str, parse_mode: str | None = None) -> dict:
        data = {"chat_id": settings.owner_chat_id, "message_id": message_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        return self._retry("editMessageText", data)

    def answer_callback(self, callback_id: str | None) -> dict:
        data = {"callback_query_id": callback_id or ""}
        return self._retry("answerCallbackQuery", data)

    def get_updates(self, offset: int, timeout: int = 30) -> dict:
        data = {
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["callback_query", "message"],
        }
        try:
            return self._retry("getUpdates", data, timeout=timeout + 5)
        except BotConflict:
            logger.warning("Bot 409 Conflict. Another instance is running.")
            time.sleep(5)
            return {"ok": True, "result": []}


bot = BotClient()
