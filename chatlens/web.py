"""ChatLens Flask web server."""

from flask import Flask, jsonify, render_template, request

from chatlens.analyzer import ChatAnalyzer
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


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(force=True)
    chat_name = data.get("chat_name", "")
    messages = _store.get_messages(chat_name)
    if not messages:
        return jsonify({"error": f"No messages for '{chat_name}'."}), 404
    result = _get_analyzer().full_analysis(messages)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
