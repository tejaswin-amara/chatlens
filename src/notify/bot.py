import json
import threading
import time

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.time()
            elapsed = max(0.0, now - self.last_update)
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            needed = 1.0 - self.tokens
            wait_time = needed / self.refill_rate
            self.tokens = 0.0
            self.last_update = now + wait_time
        if wait_time > 0:
            time.sleep(wait_time)


class TelegramRateLimiter:
    """Multi-tier token-bucket rate limiter enforcing [R-BAN-1]."""

    def __init__(self) -> None:
        self.global_bucket = TokenBucket(
            capacity=settings.telegram_global_rate_limit_rps,
            refill_rate=settings.telegram_global_rate_limit_rps,
        )
        self._chat_buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _get_chat_bucket(self, chat_id: int | str) -> TokenBucket:
        cid_str = str(chat_id)
        with self._lock:
            if cid_str not in self._chat_buckets:
                try:
                    cid_int = int(cid_str)
                    is_group = cid_int < 0
                except ValueError:
                    is_group = False

                if is_group:
                    # Group chat: max 20 msgs / min [R-BAN-1]
                    self._chat_buckets[cid_str] = TokenBucket(
                        capacity=settings.telegram_group_rate_limit_rpm,
                        refill_rate=settings.telegram_group_rate_limit_rpm / 60.0,
                    )
                else:
                    # Target user chat: max 1 msg / sec [R-BAN-1]
                    self._chat_buckets[cid_str] = TokenBucket(
                        capacity=1.0,
                        refill_rate=settings.telegram_user_rate_limit_rps,
                    )
            return self._chat_buckets[cid_str]

    def throttle(self, chat_id: int | str | None) -> None:
        # Check and enforce persistent backoff from SQLite meta [R-BAN-1]
        from src.utils.deduplication import deduplicator

        stored_backoff = deduplicator.meta_get("telegram_backoff_until")
        if stored_backoff:
            try:
                backoff_until = float(stored_backoff)
                now = time.time()
                if now < backoff_until:
                    sleep_sec = backoff_until - now
                    logger.warning(
                        "Active Telegram FloodWait backoff, sleeping", sleep_sec=sleep_sec
                    )
                    time.sleep(sleep_sec)
            except ValueError:
                pass

        # Global throttle (max 25 msgs / sec)
        self.global_bucket.acquire()

        # Chat-level throttle (1 msg/s user, 20 msgs/min group)
        if chat_id is not None:
            bucket = self._get_chat_bucket(chat_id)
            bucket.acquire()


rate_limiter = TelegramRateLimiter()


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

    def is_contact_consented(self, chat_id: int | str) -> bool:
        """Verify user has explicitly consented via /start or is the owner [R-BAN-2]."""
        from src.utils.deduplication import deduplicator

        cid_str = str(chat_id)
        if settings.owner_chat_id and cid_str == str(settings.owner_chat_id):
            return True

        try:
            cid_int = int(cid_str)
            if cid_int < 0:
                return True
        except ValueError:
            pass

        consent = deduplicator.meta_get(f"consent:{cid_str}")
        return consent is not None

    def is_group_reply_permitted(
        self, chat_id: int | str, text: str, is_high_confidence: bool = False
    ) -> bool:
        """Enforce group reply restrictions [R-BAN-2]."""
        try:
            if int(str(chat_id)) >= 0:
                return True
        except ValueError:
            return True

        is_command = text.strip().startswith("/")
        is_mention = "@" in text or "bot" in text.lower()
        return is_command or is_mention or is_high_confidence

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
        if data and "chat_id" in data:
            rate_limiter.throttle(data["chat_id"])

        for attempt in range(2):
            try:
                return self._request(endpoint, data, timeout)
            except BotRateLimitedError as e:
                from src.utils.deduplication import deduplicator

                pause_seconds = min(e.retry_after, 60)
                backoff_until = time.time() + pause_seconds + 2
                deduplicator.meta_set("telegram_backoff_until", str(backoff_until))
                logger.warning(
                    "Telegram rate limited (429/FloodWait). Pausing for wait_seconds + 2",
                    retry_after=e.retry_after,
                    pause_seconds=pause_seconds,
                    attempt=attempt,
                )
                time.sleep(pause_seconds)
            except BotError as e:
                import re

                if "HTTPError" in str(e):
                    code_str = re.search(r"HTTPError (\d+):", str(e))
                    if code_str and int(code_str.group(1)) < 500:
                        raise e
                time.sleep(2**attempt)
            except Exception:
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

        # [R-BAN-2] Verify contact consent for private chats
        if not self.is_contact_consented(target_chat_id):
            logger.warning(
                "Unsolicited direct message blocked by [R-BAN-2]",
                target_chat_id=target_chat_id,
            )
            return {"ok": False, "description": "Blocked: User has not consented via /start"}

        # [R-BAN-2] Verify group reply permissions
        if not self.is_group_reply_permitted(target_chat_id, text):
            logger.warning(
                "Unsolicited group message blocked by [R-BAN-2]",
                target_chat_id=target_chat_id,
            )
            return {"ok": False, "description": "Blocked: Unsolicited group message"}

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
