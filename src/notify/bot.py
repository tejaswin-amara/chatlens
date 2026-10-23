import json
import time

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BotRateLimitedError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"429:{retry_after}")


BotRateLimited = BotRateLimitedError


class BotConflictError(Exception):
    def __init__(self):
        super().__init__("409:Conflict")


BotConflict = BotConflictError


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
        if not url.startswith("https://api.telegram.org/"):
            raise ValueError("Invalid URL scheme")

        import urllib.error
        import urllib.request

        req = urllib.request.Request(url)  # noqa: S310
        req.add_header("Content-Type", "application/json")

        payload = json.dumps(data).encode("utf-8") if data else None

        try:
            with urllib.request.urlopen(req, data=payload, timeout=timeout) as response:  # noqa: S310
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                err_data = json.loads(e.read().decode())
                retry_after = min(err_data.get("parameters", {}).get("retry_after", 1), 60)
                raise BotRateLimitedError(retry_after) from e
            if e.code == 409:
                raise BotConflictError() from e
            err_msg = e.read().decode()
            if self.token:
                err_msg = err_msg.replace(self.token, "***")
            raise BotError(f"Telegram Bot HTTPError {e.code}: {err_msg}") from e
        except urllib.error.URLError as e:
            err_msg = str(e)
            if self.token:
                err_msg = err_msg.replace(self.token, "***")
            raise BotError(f"Telegram Bot URLError: {err_msg}") from e

    def _retry(self, endpoint: str, data: dict, timeout: int = 30):
        for attempt in range(2):
            try:
                return self._request(endpoint, data, timeout)
            except BotRateLimitedError as e:
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

    def send(
        self,
        text: str,
        buttons: list | None = None,
        parse_mode: str | None = None,
        chat_id: int | str | None = None,
    ) -> dict:
        target_chat_id = chat_id if chat_id is not None else settings.owner_chat_id
        if not target_chat_id:
            logger.warning("No chat_id or owner_chat_id configured for bot.send")
            return {"ok": False, "description": "No chat_id"}

        data: dict = {"chat_id": target_chat_id, "text": text}
        chosen_parse_mode = parse_mode
        if not chosen_parse_mode and ("**" in text or "`" in text or "*" in text):
            chosen_parse_mode = "Markdown"

        if chosen_parse_mode:
            data["parse_mode"] = chosen_parse_mode

        if buttons is not None:
            if buttons:
                inline_kb = buttons if isinstance(buttons[0], list) else [buttons]
                data["reply_markup"] = {"inline_keyboard": inline_kb}
        else:
            # Default quick-action buttons on every chat response
            data["reply_markup"] = {
                "inline_keyboard": [
                    [
                        {"text": "📅 Today", "callback_data": "cmd:today"},
                        {"text": "📊 Attendance", "callback_data": "cmd:attendance"},
                    ],
                    [
                        {"text": "⏰ Deadlines", "callback_data": "cmd:deadlines"},
                        {"text": "🟢 Status", "callback_data": "cmd:status"},
                    ],
                ]
            }

        try:
            return self._retry("sendMessage", data)
        except BotError as e:
            if chosen_parse_mode and "400" in str(e):
                logger.warning(
                    "Markdown formatting rejected by Telegram, retrying as plain text",
                    error=str(e),
                )
                data.pop("parse_mode", None)
                return self._retry("sendMessage", data)
            raise

    def edit(
        self,
        message_id: int | str,
        text: str,
        parse_mode: str | None = None,
        chat_id: int | str | None = None,
    ) -> dict:
        target_chat_id = chat_id if chat_id is not None else settings.owner_chat_id
        data = {"chat_id": target_chat_id, "message_id": message_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        try:
            return self._retry("editMessageText", data)
        except BotError as e:
            if parse_mode and "400" in str(e):
                data.pop("parse_mode", None)
                return self._retry("editMessageText", data)
            raise

    def answer_callback(self, callback_id: str | None, text: str | None = None) -> dict:
        data: dict = {"callback_query_id": callback_id or ""}
        if text:
            data["text"] = text
        return self._retry("answerCallbackQuery", data)

    def delete_webhook(self, drop_pending_updates: bool = False) -> dict:
        if not self.base_url:
            return {"ok": False, "description": "BOT_TOKEN is not set"}
        data = {"drop_pending_updates": drop_pending_updates}
        try:
            return self._request("deleteWebhook", data)
        except Exception as e:
            logger.debug("Failed to delete webhook", error=str(e))
            return {"ok": False, "description": str(e)}

    def set_my_commands(self) -> dict:
        if not self.base_url:
            return {"ok": False, "description": "BOT_TOKEN is not set"}
        commands = [
            {"command": "today", "description": "Today's classes, rooms & status"},
            {"command": "attendance", "description": "Live attendance & safe bunks"},
            {"command": "deadlines", "description": "Upcoming deadlines & milestones"},
            {"command": "status", "description": "Live daemon & chat monitoring status"},
            {"command": "marks", "description": "In-sem assessment marks"},
            {"command": "cgpa", "description": "Official academic grades & CGPA"},
            {"command": "fee", "description": "Fee orders & payment receipts"},
            {"command": "rescan", "description": "Rescan course group chats"},
            {"command": "undo", "description": "Undo last applied calendar change"},
            {"command": "help", "description": "Show all available options"},
        ]
        data = {"commands": commands}
        try:
            return self._request("setMyCommands", data)
        except Exception as e:
            logger.debug("Failed to set bot commands", error=str(e))
            return {"ok": False, "description": str(e)}

    def get_updates(self, offset: int, timeout: int = 30) -> dict:
        data = {
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["callback_query", "message"],
        }
        try:
            return self._retry("getUpdates", data, timeout=timeout + 5)
        except BotConflictError:
            logger.warning("Bot 409 Conflict. Another instance is running.")
            time.sleep(5)
            return {"ok": True, "result": []}


bot = BotClient()
