"""ChatLens FastAPI web server."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from chatlens.analyzer import ChatAnalyzer
from chatlens.storage import AsyncMessageStore

app = FastAPI(title="ChatLens API")
templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))

_store = AsyncMessageStore()
_analyzer = None


def _get_analyzer() -> ChatAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ChatAnalyzer()
    return _analyzer


@app.on_event("startup")
async def startup_event():
    await _store.create_tables()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/chats")
async def api_chats():
    return await _store.get_chat_names()


@app.get("/api/messages")
async def api_messages(chat: str = "", limit: int = 100, offset: int = 0):
    return await _store.get_messages(chat, limit=limit, offset=offset)


@app.get("/api/stats")
async def api_stats():
    return await _store.get_stats()


@app.post("/api/ask")
async def api_ask(request: Request):
    data = await request.json()
    question = data.get("question", "")
    chat_name = data.get("chat_name")
    context = await _store.search(question, limit=30)
    if chat_name:
        context = [m for m in context if m["chat_name"] == chat_name]
    if not context:
        return {"answer": "No relevant messages found for that question."}
    answer = await _get_analyzer().ask_async(question, context)
    return {"answer": answer}


@app.post("/api/summarize")
async def api_summarize(request: Request):
    data = await request.json()
    chat_name = data.get("chat_name", "")
    messages = await _store.get_messages(chat_name)
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{chat_name}'.")
    summary = await _get_analyzer().summarize_async(messages)
    return {"summary": summary}


@app.post("/api/analyze")
async def api_analyze(request: Request):
    data = await request.json()
    chat_name = data.get("chat_name", "")
    messages = await _store.get_messages(chat_name)
    if not messages:
        raise HTTPException(status_code=404, detail=f"No messages for '{chat_name}'.")
    return await _get_analyzer().full_analysis_async(messages)
