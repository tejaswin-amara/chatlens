"""Async SQLAlchemy-backed message store."""

import asyncio
import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from chatlens.db import AsyncSessionLocal, init_db
from chatlens.models import Message


def _row_to_dict(row: Message) -> dict:
    return {
        "id": row.id,
        "platform": row.platform,
        "chat_name": row.chat_name,
        "sender": row.sender,
        "timestamp": row.timestamp,
        "text": row.text,
        "reply_to": row.reply_to,
        "forwarded_from": row.forwarded_from,
        "metadata_json": row.metadata_json,
        "content_hash": row.content_hash,
    }


class AsyncMessageStore:
    _initialized = False
    _init_lock = asyncio.Lock()

    def __init__(self, session_factory=AsyncSessionLocal):
        self._session_factory = session_factory

    async def _ensure_initialized(self):
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await init_db()
            self._initialized = True

    @staticmethod
    def _content_hash(msg: dict) -> str:
        key = (
            f"{msg.get('platform')}|{msg.get('chat_name')}|{msg.get('sender')}|"
            f"{msg.get('timestamp')}|{msg.get('text')}"
        )
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_tables(self):
        await self._ensure_initialized()

    async def ingest(self, messages: list[dict]) -> int:
        """Bulk insert messages, skipping duplicates. Returns count of inserted rows."""
        await self._ensure_initialized()
        inserted = 0
        async with self._session_factory() as session:
            for msg in messages:
                record = Message(
                    platform=msg.get("platform"),
                    chat_name=msg.get("chat_name"),
                    sender=msg.get("sender"),
                    timestamp=msg.get("timestamp"),
                    text=msg.get("text"),
                    reply_to=msg.get("reply_to"),
                    forwarded_from=msg.get("forwarded_from"),
                    metadata_json=(
                        json.dumps(msg.get("metadata")) if msg.get("metadata") else None
                    ),
                    content_hash=self._content_hash(msg),
                )
                savepoint = await session.begin_nested()
                try:
                    session.add(record)
                    await session.flush()
                    await savepoint.commit()
                    inserted += 1
                except IntegrityError:
                    await savepoint.rollback()
            await session.commit()
        return inserted

    async def search(self, query: str, limit: int = 50) -> list[dict]:
        """Search messages by text content."""
        await self._ensure_initialized()
        pattern = f"%{query}%"
        async with self._session_factory() as session:
            stmt = (
                select(Message)
                .where(Message.text.ilike(pattern))
                .order_by(Message.timestamp.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_dict(row) for row in rows]

    async def get_chat_names(self) -> list[dict]:
        """List all chats with message counts."""
        await self._ensure_initialized()
        async with self._session_factory() as session:
            stmt = (
                select(
                    Message.chat_name.label("name"),
                    Message.platform,
                    func.count(Message.id).label("message_count"),
                )
                .group_by(Message.chat_name, Message.platform)
                .order_by(func.count(Message.id).desc())
            )
            rows = (await session.execute(stmt)).all()
            return [
                {
                    "name": row.name,
                    "platform": row.platform,
                    "message_count": row.message_count,
                }
                for row in rows
            ]

    async def get_messages(
        self,
        chat_name: str,
        limit: int = 500,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Retrieve messages for a chat with optional date filtering."""
        await self._ensure_initialized()
        async with self._session_factory() as session:
            stmt = select(Message).where(Message.chat_name == chat_name)
            if date_from:
                stmt = stmt.where(Message.timestamp >= date_from)
            if date_to:
                stmt = stmt.where(Message.timestamp <= date_to)
            stmt = stmt.order_by(Message.timestamp.asc()).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_dict(row) for row in rows]

    async def get_stats(self) -> dict:
        """Return summary statistics about the stored messages."""
        await self._ensure_initialized()
        async with self._session_factory() as session:
            stats_stmt = select(
                func.count(Message.id).label("total"),
                func.count(func.distinct(Message.chat_name)).label("chats"),
                func.min(Message.timestamp).label("earliest"),
                func.max(Message.timestamp).label("latest"),
            )
            stats_row = (await session.execute(stats_stmt)).one()

            platform_stmt = (
                select(Message.platform, func.count(Message.id).label("count"))
                .group_by(Message.platform)
            )
            platform_rows = (await session.execute(platform_stmt)).all()

            return {
                "total_messages": stats_row.total,
                "total_chats": stats_row.chats,
                "date_range": {"from": stats_row.earliest, "to": stats_row.latest},
                "per_platform": {row.platform: row.count for row in platform_rows},
            }

    async def close(self):
        return None


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError(
        "Synchronous MessageStore cannot be used inside an active event loop. "
        "Use AsyncMessageStore instead."
    )


class MessageStore:
    """Sync compatibility wrapper around AsyncMessageStore."""

    def __init__(self):
        self._store = AsyncMessageStore()

    def ingest(self, messages: list[dict]) -> int:
        return _run(self._store.ingest(messages))

    def search(self, query: str, limit: int = 50) -> list[dict]:
        return _run(self._store.search(query, limit=limit))

    def get_chat_names(self) -> list[dict]:
        return _run(self._store.get_chat_names())

    def get_messages(
        self,
        chat_name: str,
        limit: int = 500,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        return _run(
            self._store.get_messages(
                chat_name=chat_name,
                limit=limit,
                offset=offset,
                date_from=date_from,
                date_to=date_to,
            )
        )

    def get_stats(self) -> dict:
        return _run(self._store.get_stats())

    def close(self):
        _run(self._store.close())
