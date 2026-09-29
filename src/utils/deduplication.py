"""Hash-based deduplication cache to prevent re-processing identical messages."""

import hashlib
import time


class MessageDeduplicator:
    def __init__(self, ttl_seconds: int = 86400, max_size: int = 10000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._seen: dict[str, float] = {}

    def _compute_hash(self, chat_id: int | str, message_id: int | str, content: str = "") -> str:
        raw_key = f"{chat_id}:{message_id}:{content.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def is_duplicate(self, chat_id: int | str, message_id: int | str, content: str = "") -> bool:
        self._cleanup()
        msg_hash = self._compute_hash(chat_id, message_id, content)
        if msg_hash in self._seen:
            timestamp = self._seen[msg_hash]
            if time.time() - timestamp < self.ttl_seconds:
                return True
            del self._seen[msg_hash]
        return False

    def mark_processed(self, chat_id: int | str, message_id: int | str, content: str = "") -> str:
        self._cleanup()
        msg_hash = self._compute_hash(chat_id, message_id, content)
        self._seen[msg_hash] = time.time()
        return msg_hash

    def _cleanup(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._seen.items() if now - v > self.ttl_seconds]
        for k in expired_keys:
            del self._seen[k]

        if len(self._seen) > self.max_size:
            sorted_keys = sorted(self._seen.keys(), key=lambda k: self._seen[k])
            keys_to_remove = sorted_keys[: len(self._seen) - self.max_size]
            for k in keys_to_remove:
                del self._seen[k]


deduplicator = MessageDeduplicator()
