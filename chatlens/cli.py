"""ChatLens CLI — Click-based command-line interface."""

import click

from chatlens.storage import MessageStore


@click.group()
def cli():
    """🔍 ChatLens — AI-powered chat analysis tool."""


# ── Import subgroup ───────────────────────────────────────────────

@cli.group("import")
def import_group():
    """Import chat exports into the database."""


@import_group.command("telegram")
@click.argument("path", type=click.Path(exists=True))
def import_telegram(path: str):
    """Import a Telegram Desktop JSON export."""
    from chatlens.parsers.telegram import parse_telegram_export

    click.echo(f"Parsing {path}...")
    messages = parse_telegram_export(path)
    click.echo(click.style(f"Parsed {len(messages)} messages.", fg="cyan"))
    store = MessageStore()
    inserted = store.ingest(messages)
    click.echo(click.style(f"Ingested {inserted} new messages.", fg="green"))


@import_group.command("whatsapp")
@click.argument("path", type=click.Path(exists=True))
def import_whatsapp(path: str):
    """Import a WhatsApp exported .txt chat file."""
    from chatlens.parsers.whatsapp import parse_whatsapp_export

    click.echo(f"Parsing {path}...")
    messages = parse_whatsapp_export(path)
    click.echo(click.style(f"Parsed {len(messages)} messages.", fg="cyan"))
    store = MessageStore()
    inserted = store.ingest(messages)
    click.echo(click.style(f"Ingested {inserted} new messages.", fg="green"))


@import_group.command("telegram-live")
@click.option("--chat", multiple=True, help="Chat name(s) to fetch. Omit for all.")
@click.option("--limit", default=1000, help="Max messages per chat.")
def import_telegram_live(chat: tuple[str, ...], limit: int):
    """Fetch messages from Telegram via live API."""
    from chatlens.parsers.telegram_live import fetch_telegram_chats

    names = list(chat) if chat else None
    click.echo("Connecting to Telegram...")
    messages = fetch_telegram_chats(chat_names=names, limit=limit)
    click.echo(click.style(f"Fetched {len(messages)} messages.", fg="cyan"))
    store = MessageStore()
    inserted = store.ingest(messages)
    click.echo(click.style(f"Ingested {inserted} new messages.", fg="green"))


# ── Top-level commands ────────────────────────────────────────────

@cli.command("list")
def list_chats():
    """Show imported chats with message counts."""
    store = MessageStore()
    chats = store.get_chat_names()
    if not chats:
        click.echo("No chats imported yet.")
        return
    for c in chats:
        badge = click.style(f"[{c['platform']}]", fg="blue" if c["platform"] == "telegram" else "green")
        click.echo(f"  {badge} {c['name']}  ({c['message_count']} messages)")


@cli.command()
@click.argument("chat_name")
def summarize(chat_name: str):
    """AI summary of a chat."""
    from chatlens.analyzer import ChatAnalyzer

    store = MessageStore()
    messages = store.get_messages(chat_name)
    if not messages:
        click.echo(click.style(f"No messages found for '{chat_name}'.", fg="red"))
        return
    click.echo(f"Summarizing {len(messages)} messages...")
    result = ChatAnalyzer().summarize(messages)
    click.echo(click.style("\n── Summary ──", fg="cyan"))
    click.echo(result)


@cli.command()
@click.argument("chat_name")
def analyze(chat_name: str):
    """Full analysis (summary, sentiment, topics, relationships, timeline)."""
    from chatlens.analyzer import ChatAnalyzer

    store = MessageStore()
    messages = store.get_messages(chat_name)
    if not messages:
        click.echo(click.style(f"No messages found for '{chat_name}'.", fg="red"))
        return
    click.echo(f"Analyzing {len(messages)} messages (this may take a moment)...")
    results = ChatAnalyzer().full_analysis(messages)
    for section, text in results.items():
        click.echo(click.style(f"\n── {section.title()} ──", fg="cyan"))
        click.echo(text)


@cli.command()
@click.argument("question")
@click.option("--chat", default=None, help="Limit search to a specific chat.")
def ask(question: str, chat: str | None):
    """Ask a question — searches messages and sends context to Gemini."""
    from chatlens.analyzer import ChatAnalyzer

    store = MessageStore()
    context = store.search(question, limit=30)
    if chat:
        context = [m for m in context if m["chat_name"] == chat]
    if not context:
        click.echo("No relevant messages found.")
        return
    click.echo(f"Found {len(context)} relevant messages. Asking AI...")
    result = ChatAnalyzer().ask(question, context)
    click.echo(click.style("\n── Answer ──", fg="cyan"))
    click.echo(result)


@cli.command()
@click.argument("query")
@click.option("--limit", default=20, help="Max results.")
def search(query: str, limit: int):
    """Keyword search across all messages."""
    store = MessageStore()
    results = store.search(query, limit=limit)
    if not results:
        click.echo("No matches.")
        return
    for m in results:
        badge = click.style(f"[{m['chat_name']}]", fg="yellow")
        sender = click.style(m["sender"], fg="cyan")
        click.echo(f"  {badge} {sender} ({m['timestamp']}): {m['text'][:120]}")


@cli.command()
@click.option("--port", default=5000, help="Port to run on.")
def web(port: int):
    """Start the ChatLens web server."""
    from chatlens.web import app

    click.echo(click.style(f"Starting ChatLens web UI on http://localhost:{port}", fg="cyan"))
    app.run(debug=True, port=port)


if __name__ == "__main__":
    cli()
