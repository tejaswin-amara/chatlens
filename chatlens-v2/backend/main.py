import os
import uuid
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from pydantic import BaseModel
from typing import Optional

from database import engine, get_db
from models import Base, Message
from celery_worker import parse_file_task
from analyzer import ChatAnalyzer
from tenacity import RetryError
from parsers.telegram_live import check_status, send_code, verify_code, _fetch
from celery_worker import save_messages

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(title="ChatLens v2.0 Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RetryError)
async def retry_error_handler(request: Request, exc: RetryError):
    return JSONResponse(status_code=503, content={"error": "AI provider quota exceeded or service unavailable."})

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
        "forwarded_from": msg.forwarded_from
    }

class AskRequest(BaseModel):
    question: str
    chat_name: Optional[str] = None

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

async def handle_upload(file: UploadFile, platform: str):
    MAX_SIZE = 50 * 1024 * 1024  # 50 MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50 MB.")
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Send task to celery
    parse_file_task.delay(os.path.abspath(file_path), platform)
    return {"status": "processing", "file_path": file_path, "platform": platform}

@app.get("/api/chats")
async def get_chats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message.chat_name, Message.platform, func.count(Message.id)).group_by(Message.chat_name, Message.platform).order_by(func.count(Message.id).desc()))
    return [{"name": row[0], "platform": row[1], "message_count": row[2]} for row in result.all() if row[0] is not None]

@app.get("/api/messages")
async def get_messages(chat_name: str, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    limit = min(limit, 500)
    result = await db.execute(
        select(Message).where(Message.chat_name == chat_name).order_by(Message.timestamp.asc()).offset(skip).limit(limit)
    )
    return [message_to_dict(msg) for msg in result.scalars().all()]

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Message.id)))
    chats = await db.scalar(select(func.count(Message.chat_name.distinct())))
    earliest = await db.scalar(select(func.min(Message.timestamp)))
    latest = await db.scalar(select(func.max(Message.timestamp)))
    
    platforms = await db.execute(select(Message.platform, func.count(Message.id)).group_by(Message.platform))
    per_platform = {row[0]: row[1] for row in platforms.all() if row[0]}
    
    return {
        "total_messages": total or 0,
        "total_chats": chats or 0,
        "date_range": {"from": earliest, "to": latest},
        "per_platform": per_platform,
    }

@app.get("/api/chats/{chat_name}/stats")
async def get_chat_stats(chat_name: str, db: AsyncSession = Depends(get_db)):
    total_msgs = await db.scalar(select(func.count(Message.id)).where(Message.chat_name == chat_name)) or 0
    top_senders_res = await db.execute(
        select(Message.sender, func.count(Message.id)).where(Message.chat_name == chat_name).group_by(Message.sender).order_by(func.count(Message.id).desc()).limit(5)
    )
    top_senders = [{"name": r[0], "count": r[1]} for r in top_senders_res.all()]
    
    result = await db.execute(select(Message.sender, Message.timestamp, Message.text).where(Message.chat_name == chat_name).order_by(Message.timestamp.asc()))
    rows = result.all()
    
    stats = {
        "total_messages": total_msgs,
        "total_words": 0,
        "top_senders": top_senders,
        "awards": {},
        "activity_by_hour": {i: 0 for i in range(24)},
        "activity_by_day": {i: 0 for i in range(7)}
    }
    if not rows:
        return stats
        
    sender_stats = {}
    last_timestamp = None
    last_sender = None
    
    for r in rows:
        sender, ts_str, text = r[0], r[1], r[2] or ""
        words = len(text.split())
        stats["total_words"] += words
        
        if sender not in sender_stats:
            sender_stats[sender] = {"messages": 0, "words": 0, "monologue_max_length": 0, "response_times": [], "starters": 0}
            
        sender_stats[sender]["messages"] += 1
        sender_stats[sender]["words"] += words
        sender_stats[sender]["monologue_max_length"] = max(sender_stats[sender]["monologue_max_length"], len(text))
        
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
        except Exception:
            pass

    if sender_stats:
        top_talker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
        stats["awards"]["🗣️ Top Talker"] = f"{top_talker} ({sender_stats[top_talker]['messages']} msgs)"
        
        if len(sender_stats) > 1:
            observer = min(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
            stats["awards"]["👀 The Observer"] = f"{observer} (only {sender_stats[observer]['messages']} msgs)"
            
        monologuer = max(sender_stats.keys(), key=lambda s: sender_stats[s]["monologue_max_length"])
        stats["awards"]["📜 The Monologuer"] = f"{monologuer} ({sender_stats[monologuer]['monologue_max_length']} chars in one msg)"
        
        icebreaker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["starters"])
        if sender_stats[icebreaker]["starters"] > 0:
            stats["awards"]["🧊 The Icebreaker"] = f"{icebreaker} ({sender_stats[icebreaker]['starters']} times)"
            
        valid_speeders = {s: sum(sender_stats[s]["response_times"])/len(sender_stats[s]["response_times"]) 
                          for s in sender_stats if len(sender_stats[s]["response_times"]) >= 5}
        if valid_speeders:
            speed_demon = min(valid_speeders.keys(), key=lambda s: valid_speeders[s])
            stats["awards"]["⚡ Speed Demon"] = f"{speed_demon} (~{int(valid_speeders[speed_demon])}s avg reply)"

    return stats

@app.get("/api/global_summarize")
async def api_global_summarize(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).order_by(Message.timestamp.desc()).limit(2000))
    messages = [message_to_dict(msg) for msg in reversed(result.scalars().all())]
    if not messages:
        return {"summary": "No chats have been imported yet. Import a chat to see your summary."}
    
    summary = await asyncio.to_thread(get_analyzer().summarize, messages)
    return {"summary": summary}

@app.post("/api/analyze")
async def api_analyze(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.chat_name == req.chat_name).order_by(Message.timestamp.asc()).limit(2000))
    messages = [message_to_dict(msg) for msg in result.scalars().all()]
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{req.chat_name}'.")
        
    analysis = await asyncio.to_thread(get_analyzer().full_analysis, messages)
    return analysis

@app.post("/api/ask")
async def api_ask(req: AskRequest, db: AsyncSession = Depends(get_db)):
    # ponytail lazy: fallback to recent messages context instead of pgvector FTS, to minimize code.
    # We load last 1000 messages from the chat, or global if not specified.
    query = select(Message)
    if req.chat_name:
        query = query.where(Message.chat_name == req.chat_name)
    query = query.order_by(Message.timestamp.desc()).limit(1000)
    
    result = await db.execute(query)
    messages = [message_to_dict(msg) for msg in reversed(result.scalars().all())]
    if not messages:
        return {"answer": "No relevant messages found for that question."}
        
    answer = await asyncio.to_thread(get_analyzer().ask, req.question, messages)
    return {"answer": answer}

@app.post("/api/chats/{chat_name}/insights")
async def api_chat_insights(chat_name: str, req: InsightRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.chat_name == chat_name).order_by(Message.timestamp.asc()).limit(2000))
    messages = [message_to_dict(msg) for msg in result.scalars().all()]
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{chat_name}'.")
        
    try:
        insight = await asyncio.to_thread(get_analyzer().generate_insight, req.type, messages)
        return {"insight": insight}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/telegram/auth/verify")
async def api_telegram_verify(req: VerifyCodeRequest):
    try:
        success = await verify_code(req.phone, req.code, req.phone_code_hash)
        if success:
            return {"success": True}
        raise HTTPException(status_code=400, detail="Invalid code")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/telegram/auth/sync_live")
async def api_telegram_sync_live():
    try:
        messages = await _fetch(chat_names=None, limit=50)
        await save_messages(messages)
        return {"success": True, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
