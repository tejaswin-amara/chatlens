"""ChatLens Flask web server."""

import os
import tempfile
from flask import Flask, jsonify, render_template, request

from chatlens.analyzer import ChatAnalyzer
from chatlens.parsers.telegram import parse_telegram_export
from chatlens.parsers.telegram_live import fetch_telegram_chats, send_telegram_code_sync, verify_telegram_code_sync
from chatlens.parsers.whatsapp import parse_whatsapp_export
from chatlens.storage import MessageStore

app = Flask(__name__)

# ponytail: module-level singletons; fine for single-process dev server.
_store = MessageStore()
_analyzer = None


def _get_analyzer() -> ChatAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ChatAnalyzer()
    return _analyzer


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload/whatsapp", methods=["POST"])
def api_upload_whatsapp():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, 'wb') as f:
            file.save(f)
        messages = parse_whatsapp_export(path)
        _store.ingest(messages)
        return jsonify({"success": True, "count": len(messages)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(path)


@app.route("/api/upload/telegram", methods=["POST"])
def api_upload_telegram():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'wb') as f:
            file.save(f)
        messages = parse_telegram_export(path)
        _store.ingest(messages)
        return jsonify({"success": True, "count": len(messages)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(path)


@app.route("/api/telegram/auth/send_code", methods=["POST"])
def api_telegram_send_code():
    data = request.get_json(force=True)
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Phone number required"}), 400
    try:
        phone_code_hash = send_telegram_code_sync(phone)
        return jsonify({"success": True, "phone_code_hash": phone_code_hash})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/telegram/auth/verify", methods=["POST"])
def api_telegram_verify():
    data = request.get_json(force=True)
    phone = data.get("phone")
    code = data.get("code")
    phone_code_hash = data.get("phone_code_hash")
    if not all([phone, code, phone_code_hash]):
        return jsonify({"error": "Missing parameters"}), 400
    try:
        success = verify_telegram_code_sync(phone, code, phone_code_hash)
        if success:
            # Once verified, fetch the chats
            messages = fetch_telegram_chats()
            _store.ingest(messages)
            return jsonify({"success": True, "count": len(messages)})
        return jsonify({"error": "Invalid code"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/chats")
def api_chats():
    return jsonify(_store.get_chat_names())


@app.route("/api/messages")
def api_messages():
    chat = request.args.get("chat", "")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify(_store.get_messages(chat, limit=limit, offset=offset))


@app.route("/api/stats")
def api_stats():
    return jsonify(_store.get_stats())


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json(force=True)
    question = data.get("question", "")
    chat_name = data.get("chat_name")
    context = _store.search(question, limit=30)
    if chat_name:
        context = [m for m in context if m["chat_name"] == chat_name]
    if not context:
        return jsonify({"answer": "No relevant messages found for that question."})
    answer = _get_analyzer().ask(question, context)
    return jsonify({"answer": answer})


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    data = request.get_json(force=True)
    chat_name = data.get("chat_name", "")
    messages = _store.get_messages(chat_name)
    if not messages:
        return jsonify({"error": f"No messages for '{chat_name}'."}), 404
    summary = _get_analyzer().summarize(messages)
    return jsonify({"summary": summary})


@app.route("/api/global_summarize")
def api_global_summarize():
    messages = _store.get_all_messages(limit=2000)
    if not messages:
        return jsonify({"summary": "No chats have been imported yet. Import a chat to see your summary."})
    summary = _get_analyzer().summarize(messages)
    return jsonify({"summary": summary})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(force=True)
    chat_name = data.get("chat_name", "")
    messages = _store.get_messages(chat_name)
    if not messages:
        return jsonify({"error": f"No messages for '{chat_name}'."}), 404
    result = _get_analyzer().full_analysis(messages)
    return jsonify(result)


@app.route("/api/chats/<path:chat_name>/stats")
def api_chat_stats(chat_name):
    return jsonify(_store.get_chat_stats(chat_name))


@app.route("/api/chats/<path:chat_name>/insights", methods=["POST"])
def api_chat_insights(chat_name):
    data = request.get_json(force=True)
    insight_type = data.get("type")
    if not insight_type:
        return jsonify({"error": "Missing 'type' parameter"}), 400
    messages = _store.get_messages(chat_name)
    if not messages:
        return jsonify({"error": f"No messages for '{chat_name}'."}), 404
    try:
        result = _get_analyzer().generate_insight(insight_type, messages)
        return jsonify({"insight": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
