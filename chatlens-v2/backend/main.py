import csv
import inspect
import io
import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analyzer import ChatAnalyzer
from celery_worker import celery_app, parse_and_save_sync, parse_file_task, save_messages
from database import engine, get_db
from embeddings import generate_embedding
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from firebase_auth import require_current_user
from models import Base, Message
from parsers.telegram_live import _fetch, check_status, send_code, verify_code
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import RetryError

from config import MAX_UPLOAD_BYTES

try:
    import celery.result
except ImportError:
    celery = None  # type: ignore

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore

logger = logging.getLogger(__name__)


def _escape_like(val: str) -> str:
    """Escape special characters in SQL LIKE/ILIKE patterns."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.debug(f"Database init warning: {exc}")
    yield
    # Shutdown
    try:
        await engine.dispose()
    except Exception as exc:
        logger.debug(f"Engine dispose warning: {exc}")


app = FastAPI(title="ChatLens v2.0 Backend", lifespan=lifespan)

cors_origins_env = os.getenv("CORS_ORIGINS")
allowed_origins = (
    [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    if cors_origins_env
    else ["http://localhost:3000", "http://127.0.0.1:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/healthz")
async def healthz() -> dict[str, str]:
    """Health and readiness probe."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/status")
async def status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Liveness, readiness, and active database connectivity probe."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e!s}"
    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "version": "2.0.0",
        "database": db_status,
    }


@app.exception_handler(RetryError)
async def retry_error_handler(request: Request, exc: RetryError):
    return JSONResponse(
        status_code=503, content={"error": "AI provider quota exceeded or service unavailable."}
    )


_analyzer = None


def get_analyzer() -> ChatAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ChatAnalyzer()
    return _analyzer


def message_to_dict(msg: Message) -> dict:
    return {
        "id": msg.id,
        "platform": msg.platform,
        "chat_name": msg.chat_name,
        "sender": msg.sender,
        "timestamp": msg.timestamp,
        "text": msg.text,
        "reply_to": msg.reply_to,
        "forwarded_from": msg.forwarded_from,
    }


class AskRequest(BaseModel):
    question: str
    chat_name: str | None = None


class ChatRequest(BaseModel):
    chat_name: str


class InsightRequest(BaseModel):
    type: str


@app.post("/api/upload/whatsapp")
async def upload_whatsapp(file: UploadFile = File(...)):
    return await handle_upload(file, "whatsapp")


@app.post("/api/upload/telegram")
async def upload_telegram(file: UploadFile = File(...)):
    return await handle_upload(file, "telegram")


@app.post("/api/chats/import")
async def import_chat(file: UploadFile = File(...), platform: str | None = None):
    """Universal chat import endpoint.

    Supports WhatsApp (.txt, .zip) and Telegram (.json, .zip).
    """
    fname = (file.filename or "").lower()
    inferred = platform or ("telegram" if fname.endswith(".json") else "whatsapp")
    return await handle_upload(file, inferred)


async def handle_upload(file: UploadFile, platform: str):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES} bytes.",
        )
    os.makedirs("uploads", exist_ok=True)
    file_name = Path(file.filename or "upload").name
    file_path = f"uploads/{uuid.uuid4()}_{file_name}"
    with open(file_path, "wb") as f:
        f.write(content)

    abs_path = os.path.abspath(file_path)
    # Try Celery task dispatch; fall back to synchronous if Redis/Celery unavailable
    try:
        task = parse_file_task.delay(abs_path, platform)
        return {"status": "processing", "task_id": task.id, "platform": platform}
    except Exception as exc:
        # Fallback to synchronous in-process parsing
        res = parse_and_save_sync(abs_path, platform)
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("error", "Parsing failed")) from exc
        return {"status": "done", "count": res.get("count", 0), "platform": platform}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Poll Celery task status for background imports."""
    try:
        if celery is None or not hasattr(celery, "result"):
            return {"status": "FAILURE", "error": "Celery not available"}

        res = celery.result.AsyncResult(task_id, app=celery_app)
        if res.ready():
            val = res.result
            if isinstance(val, dict):
                return {
                    "status": "SUCCESS" if val.get("status") == "done" else "FAILURE",
                    "count": val.get("count", 0),
                    "error": val.get("error"),
                }
            return {"status": res.status, "result": str(val)}
        return {"status": res.status, "info": res.info}
    except Exception as e:
        return {"status": "UNKNOWN", "error": str(e)}


@app.get("/api/chats")
async def get_chats(db: AsyncSession = Depends(get_db)):
    result: Any = await db.execute(
        select(Message.chat_name, Message.platform, func.count(Message.id))
        .group_by(Message.chat_name, Message.platform)
        .order_by(func.count(Message.id).desc())
    )
    return [
        {"name": row[0], "platform": row[1], "message_count": row[2]}
        for row in result.all()
        if row[0] is not None
    ]


@app.delete("/api/chats/{chat_name}")
async def delete_chat(chat_name: str, db: AsyncSession = Depends(get_db)):
    """Delete all messages associated with a chat."""
    result = await db.execute(select(func.count(Message.id)).where(Message.chat_name == chat_name))
    count = result.scalar() or 0
    if count == 0:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_name}' not found.")
    await db.execute(delete(Message).where(Message.chat_name == chat_name))
    await db.commit()
    return {"success": True, "deleted_count": count}


@app.get("/api/chats/{chat_id}/export")
async def export_chat(
    chat_id: str,
    format: str = "json",
    limit: int | None = None,
    offset: int = 0,
    skip: int = 0,
    sender: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all messages and analytics summary for a chat as JSON or CSV stream."""
    if format not in ("json", "csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Supported formats: 'json', 'csv'.",
        )

    stmt = select(Message).where(Message.chat_name == chat_id)
    if sender:
        stmt = stmt.where(Message.sender == sender)
    stmt = stmt.order_by(Message.timestamp.asc())
    effective_skip = offset if offset != 0 else skip
    if effective_skip:
        stmt = stmt.offset(effective_skip)
    if limit is not None:
        stmt = stmt.limit(limit)

    exec_res = db.execute(stmt)
    result = await exec_res if inspect.isawaitable(exec_res) else exec_res
    messages = list(result.scalars().all())
    if not messages:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found.")

    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", chat_id)

    if format == "json":
        data = {
            "chat_name": chat_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "total_messages": len(messages),
            "messages": [message_to_dict(m) for m in messages],
        }
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_export.json"'},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "platform", "chat_name", "sender", "timestamp", "text", "reply_to", "forwarded_from"]
    )
    for m in messages:
        writer.writerow(
            [
                m.id,
                m.platform or "",
                m.chat_name or "",
                m.sender or "",
                m.timestamp or "",
                m.text or "",
                m.reply_to or "",
                m.forwarded_from or "",
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_export.csv"'},
    )


@app.get("/api/messages")
async def get_messages(
    chat_name: str,
    skip: int = 0,
    offset: int = 0,
    limit: int = 50,
    sender: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    effective_skip = offset if offset != 0 else skip
    limit = min(limit, 500)
    stmt = select(Message).where(Message.chat_name == chat_name)
    if sender:
        stmt = stmt.where(Message.sender == sender)
    stmt = stmt.order_by(Message.timestamp.asc()).offset(effective_skip).limit(limit)
    result = await db.execute(stmt)
    return [message_to_dict(msg) for msg in result.scalars().all()]


@app.get("/api/messages/search")
async def search_messages(
    chat_name: str | None = None,
    query: str | None = None,
    q: str | None = None,
    sender: str | None = None,
    skip: int = 0,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Filter messages across text query, sender name, and chat."""
    effective_query = q if q is not None else query
    effective_skip = offset if offset != 0 else skip
    stmt = select(Message)
    if chat_name:
        stmt = stmt.where(Message.chat_name == chat_name)
    if sender:
        stmt = stmt.where(Message.sender.ilike(f"%{_escape_like(sender)}%"))
    if effective_query:
        stmt = stmt.where(Message.text.ilike(f"%{_escape_like(effective_query)}%"))
    stmt = stmt.order_by(Message.timestamp.desc()).offset(effective_skip).limit(min(limit, 200))
    result = await db.execute(stmt)
    return [message_to_dict(msg) for msg in result.scalars().all()]


@app.get("/api/chats/{chat_id}/search")
async def search_chat_messages(
    chat_id: str,
    q: str | None = None,
    query: str | None = None,
    sender: str | None = None,
    skip: int = 0,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Filter messages inside a specific chat by query text or sender."""
    return await search_messages(
        chat_name=chat_id,
        query=query,
        q=q,
        sender=sender,
        skip=skip,
        offset=offset,
        limit=limit,
        db=db,
    )


@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Message.id)))
    chats = await db.scalar(select(func.count(Message.chat_name.distinct())))
    earliest = await db.scalar(select(func.min(Message.timestamp)))
    latest = await db.scalar(select(func.max(Message.timestamp)))

    platforms = await db.execute(
        select(Message.platform, func.count(Message.id)).group_by(Message.platform)
    )
    per_platform = {row[0]: row[1] for row in platforms.all() if row[0]}

    return {
        "total_messages": total or 0,
        "total_chats": chats or 0,
        "date_range": {"from": earliest, "to": latest},
        "per_platform": per_platform,
    }


@app.get("/api/chats/{chat_name}/stats")
async def get_chat_stats(chat_name: str, db: AsyncSession = Depends(get_db)):
    total_msgs = (
        await db.scalar(select(func.count(Message.id)).where(Message.chat_name == chat_name)) or 0
    )
    top_senders_res: Any = await db.execute(
        select(Message.sender, func.count(Message.id))
        .where(Message.chat_name == chat_name)
        .group_by(Message.sender)
        .order_by(func.count(Message.id).desc())
        .limit(5)
    )
    top_senders = [{"name": r[0], "count": r[1]} for r in top_senders_res.all()]

    result: Any = await db.execute(
        select(Message.sender, Message.timestamp, Message.text)
        .where(Message.chat_name == chat_name)
        .order_by(Message.timestamp.asc())
    )
    rows = result.all()

    stats = {
        "total_messages": total_msgs,
        "total_words": 0,
        "top_senders": top_senders,
        "awards": {},
        "activity_by_hour": {i: 0 for i in range(24)},
        "activity_by_day": {i: 0 for i in range(7)},
    }
    if not rows:
        return stats

    sender_stats = {}
    last_timestamp = None
    last_sender = None

    for r in rows:
        sender, ts_str, text_val = r[0], r[1], r[2] or ""
        words = len(text_val.split())
        stats["total_words"] += words

        if sender not in sender_stats:
            sender_stats[sender] = {
                "messages": 0,
                "words": 0,
                "monologue_max_length": 0,
                "response_times": [],
                "starters": 0,
            }

        sender_stats[sender]["messages"] += 1
        sender_stats[sender]["words"] += words
        sender_stats[sender]["monologue_max_length"] = max(
            sender_stats[sender]["monologue_max_length"], len(text_val)
        )

        try:
            clean_ts = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            stats["activity_by_hour"][dt.hour] += 1
            stats["activity_by_day"][dt.weekday()] += 1

            if last_timestamp and sender != last_sender:
                diff = (dt - last_timestamp).total_seconds()
                if diff > 28800:
                    sender_stats[sender]["starters"] += 1
                else:
                    sender_stats[sender]["response_times"].append(diff)
            last_timestamp = dt
            last_sender = sender
        except Exception as exc:
            logger.debug(f"Timestamp parse error: {exc}")

    if sender_stats:
        top_talker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
        stats["awards"]["🗣️ Top Talker"] = (
            f"{top_talker} ({sender_stats[top_talker]['messages']} msgs)"
        )

        if len(sender_stats) > 1:
            observer = min(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
            stats["awards"]["👀 The Observer"] = (
                f"{observer} (only {sender_stats[observer]['messages']} msgs)"
            )

        monologuer = max(sender_stats.keys(), key=lambda s: sender_stats[s]["monologue_max_length"])
        stats["awards"]["📜 The Monologuer"] = (
            f"{monologuer} ({sender_stats[monologuer]['monologue_max_length']} chars in one msg)"
        )

        icebreaker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["starters"])
        if sender_stats[icebreaker]["starters"] > 0:
            stats["awards"]["🧊 The Icebreaker"] = (
                f"{icebreaker} ({sender_stats[icebreaker]['starters']} times)"
            )

        valid_speeders = {
            s: sum(sender_stats[s]["response_times"]) / len(sender_stats[s]["response_times"])
            for s in sender_stats
            if len(sender_stats[s]["response_times"]) >= 5
        }
        if valid_speeders:
            speed_demon = min(valid_speeders.keys(), key=lambda s: valid_speeders[s])
            stats["awards"]["⚡ Speed Demon"] = (
                f"{speed_demon} (~{int(valid_speeders[speed_demon])}s avg reply)"
            )

    return stats


@app.get("/api/global_summarize")
async def api_global_summarize(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).order_by(Message.timestamp.desc()).limit(2000))
    messages = [message_to_dict(msg) for msg in reversed(result.scalars().all())]
    if not messages:
        return {"summary": "No chats have been imported yet. Import a chat to see your summary."}

    summary = await get_analyzer().summarize(messages)
    return {"summary": summary}


@app.post("/api/analyze")
async def api_analyze(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.chat_name == req.chat_name)
        .order_by(Message.timestamp.asc())
        .limit(2000)
    )
    messages = [message_to_dict(msg) for msg in result.scalars().all()]
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{req.chat_name}'.")

    analysis = await get_analyzer().full_analysis(messages)
    return analysis


async def _retrieve_relevant_messages(
    db: Any,
    chat_name: str | None = None,
    query_embedding: list[float] | None = None,
    limit: int = 100,
) -> list[Message]:
    """Retrieve relevant messages using vector semantic search when on PostgreSQL,

    or recency order under SQLite / when no query embedding is provided.
    """
    bind = getattr(db, "bind", None)
    if bind is None and hasattr(db, "get_bind"):
        try:
            bind = db.get_bind()
        except Exception:
            bind = None
    is_postgres = False
    if bind is not None and hasattr(bind, "dialect"):
        is_postgres = getattr(bind.dialect, "name", "") == "postgresql"

    # Try vector query if on PostgreSQL and embedding is provided
    if query_embedding is not None and is_postgres:
        try:
            v_query = select(Message).where(Message.embedding.isnot(None))
            if chat_name:
                v_query = v_query.where(Message.chat_name == chat_name)
            v_query = v_query.order_by(
                Message.embedding.cosine_distance(query_embedding).asc()
            ).limit(limit)
            exec_v = db.execute(v_query)
            v_result = await exec_v if inspect.isawaitable(exec_v) else exec_v
            found = list(v_result.scalars().all())
            if found:
                return sorted(found, key=lambda m: m.timestamp or "")
        except Exception as exc:
            logger.debug(f"Vector search failed, falling back to recency: {exc}")

    # Fallback to recency / chronological order
    query = select(Message)
    if chat_name:
        query = query.where(Message.chat_name == chat_name)
    query = query.order_by(Message.timestamp.asc()).limit(limit)
    exec_res = db.execute(query)
    result = await exec_res if inspect.isawaitable(exec_res) else exec_res
    return list(result.scalars().all())


@app.post("/api/ask")
async def api_ask(req: AskRequest, db: AsyncSession = Depends(get_db)):
    """Answer questions using vector semantic retrieval with fallback to recency."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    query_embedding: list[float] | None = None

    if gemini_key and genai is not None:
        try:
            client = genai.Client(api_key=gemini_key)
            query_embedding = generate_embedding(
                client,
                req.question,
                task_type="RETRIEVAL_QUERY",
                model="gemini-embedding-001",
            )
        except Exception:
            query_embedding = None

    messages = await _retrieve_relevant_messages(
        db,
        chat_name=req.chat_name,
        query_embedding=query_embedding,
        limit=100,
    )

    if not messages:
        return {"answer": "No relevant messages found for that question."}

    context_messages = [message_to_dict(msg) for msg in messages]
    answer = await get_analyzer().ask(req.question, context_messages)
    return {"answer": answer}


ask_question = api_ask


@app.post("/api/chats/{chat_name}/insights")
async def api_chat_insights(
    chat_name: str, req: InsightRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Message)
        .where(Message.chat_name == chat_name)
        .order_by(Message.timestamp.asc())
        .limit(2000)
    )
    messages = [message_to_dict(msg) for msg in result.scalars().all()]
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{chat_name}'.")

    try:
        insight = await get_analyzer().generate_insight(req.type, messages)
        return {"insight": insight}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/spark/status")
async def get_spark_status():
    """Read-only status bridge inspecting SPARK PA SQLite database (spark.db)."""
    db_path = os.getenv("SPARK_DB", "spark.db")
    if not os.path.isabs(db_path):
        candidate = os.path.join(os.getcwd(), db_path)
        if not os.path.exists(candidate):
            candidate = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), db_path
            )
        db_path = candidate

    if not os.path.exists(db_path):
        return {
            "status": "offline",
            "message": "SPARK PA database not found. Daemon has not been started yet.",
            "mode": os.getenv("SPARK_MODE", "dry"),
            "seen_messages": 0,
            "pending": [],
            "writes": [],
        }

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()

        pending_rows = []
        try:
            cur.execute(
                "SELECT id, created, status, event_json FROM pending ORDER BY id DESC LIMIT 10;"
            )
            for r in cur.fetchall():
                pending_rows.append({"id": r[0], "ts": r[1], "status": r[2], "event": r[3]})
        except sqlite3.OperationalError:
            try:
                cur.execute(
                    "SELECT id, ts, status, event_json FROM pending ORDER BY id DESC LIMIT 10;"
                )
                for r in cur.fetchall():
                    pending_rows.append({"id": r[0], "ts": r[1], "status": r[2], "event": r[3]})
            except sqlite3.OperationalError:
                pass

        writes_rows = []
        try:
            cur.execute(
                "SELECT id, ts, kind, event_id, undone FROM writes ORDER BY id DESC LIMIT 10;"
            )
            for r in cur.fetchall():
                writes_rows.append(
                    {"id": r[0], "ts": r[1], "kind": r[2], "event_id": r[3], "undone": bool(r[4])}
                )
        except sqlite3.OperationalError:
            pass

        seen_count = 0
        try:
            cur.execute("SELECT COUNT(*) FROM seen;")
            seen_count = cur.fetchone()[0]
        except sqlite3.OperationalError:
            pass

        conn.close()
        return {
            "status": "online",
            "mode": os.getenv("SPARK_MODE", "dry"),
            "seen_messages": seen_count,
            "pending": pending_rows,
            "writes": writes_rows,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


class SendCodeRequest(BaseModel):
    phone: str


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str


@app.get("/api/telegram/auth/status")
async def api_telegram_status():
    authorized = await check_status()
    return {"authorized": authorized}


@app.post("/api/telegram/auth/send_code")
async def api_telegram_send_code(req: SendCodeRequest):
    try:
        phone_code_hash = await send_code(req.phone)
        return {"success": True, "phone_code_hash": phone_code_hash}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/telegram/auth/verify")
async def api_telegram_verify(req: VerifyCodeRequest):
    try:
        success = await verify_code(req.phone, req.code, req.phone_code_hash)
        if success:
            return {"success": True}
        raise HTTPException(status_code=400, detail="Invalid code")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/telegram/auth/sync_live")
async def api_telegram_sync_live():
    try:
        messages = await _fetch(chat_names=None, limit=50)
        await save_messages(messages)
        return {"success": True, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class TimetableOverrideRequest(BaseModel):
    target_date: str | None = None
    period: int | None = None
    course_code: str
    course_name: str | None = None
    room: str | None = None
    status: str = "OVERRIDE"
    summary: str = ""


class SayDeadlinesRequest(BaseModel):
    query: str | None = None


@app.get("/api/timetable/today")
async def api_timetable_today(user: dict[str, Any] | None = Depends(require_current_user)):
    """Retrieve today's effective class timetable with real-time room overrides."""
    try:
        import src.timetable as tt
        from src.utils import clock

        today = clock.today_ist()
        timetable = tt.load()
        if not timetable:
            return {"date": today.isoformat(), "slots": [], "message": "No timetable loaded"}

        effective = tt.get_effective_slots(today, timetable)
        slots_data = []
        for s in sorted(effective, key=lambda x: x.period):
            slots_data.append(
                {
                    "period": s.period,
                    "course": s.course,
                    "room": s.room,
                    "faculty": s.faculty,
                    "override": s.override,
                    "status": "CANCELLED"
                    if s.override == "CANCELLED"
                    else ("OVERRIDE" if s.override else "NORMAL"),
                }
            )
        return {
            "date": today.isoformat(),
            "day": today.strftime("%A"),
            "slots": slots_data,
        }
    except Exception as exc:
        logger.error(f"Failed to fetch timetable: {exc}")
        return {"date": datetime.now(UTC).date().isoformat(), "slots": [], "error": str(exc)}


@app.get("/api/timetable/week")
async def api_timetable_week(user: dict[str, Any] | None = Depends(require_current_user)):
    """Retrieve all slots for the full weekly timetable."""
    try:
        import src.timetable as tt

        timetable = tt.load()
        if not timetable:
            return {"slots": []}
        return {
            "meta": {
                "term": timetable.meta.term,
                "valid_from": str(timetable.meta.valid_from),
                "valid_to": str(timetable.meta.valid_to),
            },
            "slots": [
                {
                    "day": s.day,
                    "period": s.period,
                    "course": s.course,
                    "room": s.room,
                    "faculty": s.faculty,
                }
                for s in timetable.slots
            ],
        }
    except Exception as exc:
        return {"slots": [], "error": str(exc)}


@app.post("/api/timetable/override")
async def api_timetable_override(
    req: TimetableOverrideRequest,
    user: dict[str, Any] | None = Depends(require_current_user),
):
    """Update timetable with a new room override or class cancellation."""
    try:
        from src.utils import clock
        from src.utils.deduplication import deduplicator

        target_date = req.target_date or clock.today_ist().strftime("%Y-%m-%d")
        row_id = deduplicator.record_override(
            target_date=target_date,
            period=req.period,
            course_code=req.course_code,
            course_name=req.course_name,
            room=req.room,
            status=req.status.upper(),
            summary=req.summary
            or f"Manual override via ChatLens web: {req.course_code} -> {req.room or req.status}",
        )
        return {
            "success": True,
            "id": row_id,
            "target_date": target_date,
            "course_code": req.course_code,
            "status": req.status.upper(),
            "room": req.room,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to record timetable override: {exc}"
        ) from exc


@app.get("/api/deadlines")
async def api_deadlines(user: dict[str, Any] | None = Depends(require_current_user)):
    """Retrieve upcoming academic calendar milestones and pending tasks."""
    try:
        from src.academic_calendar import load_calendar
        from src.utils import clock
        from src.utils.deduplication import deduplicator

        today = clock.today_ist()
        cal = load_calendar()
        milestones = []
        if cal:
            for term, term_dates in cal.terms.items():
                for m_name, m_date in term_dates.items():
                    if m_date >= today:
                        milestones.append(
                            {
                                "title": m_name,
                                "date": m_date.isoformat(),
                                "term": term,
                                "days_remaining": (m_date - today).days,
                            }
                        )
        milestones.sort(key=lambda x: str(x["date"]))

        pending_tasks = deduplicator.list_pending(limit=20)
        formatted_tasks = []
        for p in pending_tasks:
            ev = p.get("event", {})
            formatted_tasks.append(
                {
                    "id": p.get("id"),
                    "summary": ev.get("summary") or ev.get("description") or "Task / Assignment",
                    "status": p.get("status"),
                    "created": p.get("created"),
                }
            )

        return {
            "today": today.isoformat(),
            "milestones": milestones[:10],
            "tasks": formatted_tasks,
        }
    except Exception as exc:
        return {
            "today": datetime.now(UTC).date().isoformat(),
            "milestones": [],
            "tasks": [],
            "error": str(exc),
        }


@app.post("/api/deadlines/say")
async def api_deadlines_say(
    req: SayDeadlinesRequest | None = None,
    user: dict[str, Any] | None = Depends(require_current_user),
):
    """Use Gemini AI to synthesize a voice-ready audio briefing script."""
    try:
        import src.timetable as tt
        from src.academic_calendar import load_calendar
        from src.utils import clock

        today = clock.today_ist()
        timetable = tt.load()
        effective_today = tt.get_effective_slots(today, timetable) if timetable else []

        schedule_summary = (
            ", ".join(
                [
                    f"Period {s.period}: {s.course} in {s.room} ({s.override or 'Normal'})"
                    for s in effective_today
                ]
            )
            or "No scheduled classes today."
        )

        cal = load_calendar()
        milestone_str = ""
        if cal:
            upcoming = []
            for _term, term_dates in cal.terms.items():
                for m_name, m_date in term_dates.items():
                    if m_date >= today:
                        upcoming.append(f"{m_name} on {m_date.strftime('%d %B %Y')}")
            upcoming.sort()
            milestone_str = "; ".join(upcoming[:5])

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            script_fallback = (
                f"Good day! Today you have: {schedule_summary}. "
                f"Upcoming milestones: {milestone_str or 'None'}. "
                "Make sure to stay ahead on your courses!"
            )
            return {"script": script_fallback}

        default_query = "Give me my full briefing and say the deadlines"
        user_query = req.query if req and req.query else default_query
        prompt = (
            f"You are the personal AI executive assistant for Tejaswin Amara (student at KLEF).\n"
            f"Today is {today.strftime('%A, %d %B %Y')}.\n"
            f"Today's schedule: {schedule_summary}\n"
            f"Upcoming academic milestones: {milestone_str or 'None registered'}\n\n"
            f"User request: {user_query}.\n\n"
            "Provide a natural, energetic, spoken-style briefing script that covers "
            "today's classes, room changes, and important approaching deadlines "
            "in 3-4 spoken sentences."
        )

        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return {"script": response.text}
    except Exception as exc:
        logger.error(f"Error generating voice briefing: {exc}")
        return {"script": f"Unable to generate AI briefing at this moment: {exc}"}


@app.get("/api/monitoring/status")
async def api_monitoring_status(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] | None = Depends(require_current_user),
):
    """Retrieve live monitoring status of Telegram chats and SPARK daemon."""
    from src.config import settings

    total_msg_res = await db.execute(select(func.count(Message.id)))
    total_messages = total_msg_res.scalar() or 0

    chats_res: Any = await db.execute(
        select(Message.chat_name, func.count(Message.id)).group_by(Message.chat_name)
    )
    active_chats = [{"name": row[0], "message_count": row[1]} for row in chats_res.all()]

    spark_db_path = settings.spark_db
    spark_online = os.path.exists(spark_db_path)

    return {
        "status": "online" if spark_online else "idle",
        "monitored_chat_ids": settings.allowed_chat_ids,
        "total_monitored_chats": len(settings.allowed_chat_ids),
        "total_saved_messages": total_messages,
        "active_chats": active_chats,
        "gemini_model": settings.gemini_model,
        "spark_mode": settings.spark_mode,
    }
