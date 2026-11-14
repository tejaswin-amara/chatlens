import time
from unittest.mock import patch

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_command
from src.knowledge.document_loader import (
    DocumentKnowledgeLoader,
    chunk_text,
    extract_text_from_pdf,
)
from src.utils.deduplication import deduplicator


@pytest.fixture(autouse=True)
def clean_test_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_rag.db")
    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "owner_chat_id", 12345)
    deduplicator._db_path = test_db
    deduplicator._initialized = False
    deduplicator._ensure_db()
    yield test_db


def test_chunk_text():
    sample = "Paragraph 1\n\nParagraph 2 is slightly longer.\n\nParagraph 3 is also here."
    chunks = chunk_text(sample, max_chunk_size=30)
    assert len(chunks) >= 2
    assert "Paragraph 1" in chunks[0]


def test_extract_text_from_pdf_empty_and_corrupt(tmp_path):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    assert extract_text_from_pdf(empty_pdf) == ""

    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"Not a real PDF header\x00\xff")
    # Must not raise an error
    assert extract_text_from_pdf(corrupt_pdf) == ""


def test_extract_text_from_pdf_simple_stream(tmp_path):
    import zlib

    # Construct a minimal synthetic PDF stream
    text_content = b"BT /F1 12 Tf (Hello Academic World) Tj ET"
    compressed = zlib.compress(text_content)
    pdf_bytes = b"%PDF-1.4\nstream\n" + compressed + b"\nendstream\n%%EOF"

    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(pdf_bytes)

    extracted = extract_text_from_pdf(pdf_file)
    assert "Hello Academic World" in extracted


def test_document_knowledge_loader_indexes_files(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # 1. Text document
    notes_file = data_dir / "dlac_notes.txt"
    notes_file.write_text(
        "Deep Learning Accelerated Computing Notes\n\n"
        "DLAC covers GPU acceleration with CUDA and TensorRT.\n"
        "Lab exam is scheduled for Week 12.",
        encoding="utf-8",
    )

    # 2. Markdown document
    syllabus_file = data_dir / "syllabus.md"
    syllabus_file.write_text(
        "# Cloud Infrastructure and Services\n\n"
        "Course Code: 25CS2206E\n"
        "Section: S-11\n"
        "Faculty: Divya Priya Degala\n"
        "Room: H006",
        encoding="utf-8",
    )

    loader = DocumentKnowledgeLoader(data_dir=data_dir)
    count = loader.index_all()
    assert count >= 2

    # Verify search in SQLite
    hits = deduplicator.search_knowledge_docs("TensorRT CUDA", limit=3)
    assert len(hits) >= 1
    assert "dlac_notes.txt" in hits[0]["filename"]
    assert "[Doc: dlac_notes.txt]" in hits[0]["source"]

    cis_hits = deduplicator.search_knowledge_docs("25CS2206E H006", limit=3)
    assert len(cis_hits) >= 1
    assert "syllabus.md" in cis_hits[0]["filename"]


def test_chat_message_indexing_and_search():
    deduplicator.store_chat_message(
        chat_id=999,
        chat_name="CS Dept Notice",
        message_id=101,
        sender_name="Prof. Sharma",
        text="Reminder: Tomorrow DLAC class shifted to room H-005 period 1.",
        date="2026-11-14 10:00",
        ts=time.time(),
    )

    hits = deduplicator.search_chat_messages("DLAC class room H-005", limit=3)
    assert len(hits) == 1
    assert hits[0]["chat_name"] == "CS Dept Notice"
    assert "H-005" in hits[0]["text"]
    assert hits[0]["source"] == "[Chat: CS Dept Notice, 2026-11-14 10:00]"


@pytest.mark.asyncio
async def test_conversational_chatbot_natural_language_query(tmp_path):
    # Store knowledge
    deduplicator.store_knowledge_doc(
        filename="vlsi_viva.txt",
        chunk_index=0,
        title="VLSI Viva Schedule",
        text="VLSI Design Lab Defence is on 25 Nov 2026 in Room 302 with Dr. Alok Kumar.",
        source="[Doc: vlsi_viva.txt]",
    )

    with patch("src.notify.bot.bot.send") as mock_send:
        # User asks without slash
        msg = {"chat": {"id": 12345}, "text": "When is my VLSI Design Lab Defence?"}
        await handle_bot_command(msg)

        # Bot should respond with thinking then grounded answer
        assert mock_send.call_count >= 1
        sent_text = mock_send.call_args[0][0]
        assert "VLSI" in sent_text or "302" in sent_text
        assert "[Doc: vlsi_viva.txt]" in sent_text


@pytest.mark.asyncio
async def test_conversational_chatbot_missing_info_returns_not_found():
    with patch("src.notify.bot.bot.send") as mock_send:
        msg = {"chat": {"id": 12345}, "text": "What is the quantum mechanics syllabus?"}
        await handle_bot_command(msg)

        assert mock_send.call_count >= 1
        sent_text = mock_send.call_args[0][0]
        assert "Not found in your chats/documents." in sent_text


@pytest.mark.asyncio
async def test_index_summary_command():
    deduplicator.store_knowledge_doc(
        filename="academic_calendar_2026_27.toml",
        chunk_index=0,
        title="In-Sem 1 Exams",
        text="In-Sem 1 Examination milestone scheduled for 23 Feb 2027.",
        source="[Doc: academic_calendar_2026_27.toml]",
    )
    deduplicator.store_chat_message(
        chat_id=888,
        chat_name="Cluster 4 Official",
        message_id=202,
        sender_name="HOD",
        text="Lab report submissions must be completed before 5 PM Friday.",
        date="2026-11-14 11:00",
    )

    with patch("src.notify.bot.bot.send") as mock_send:
        msg = {"chat": {"id": 12345}, "text": "/index_summary"}
        await handle_bot_command(msg)

        mock_send.assert_called_once()
        summary = mock_send.call_args[0][0]
        assert "Executive Knowledge & Index Summary" in summary
        assert "Critical Deadlines & Exam Dates" in summary
        assert "Room & Timetable Overrides" in summary
        assert "In-Sem Assessments & Faculty Notices" in summary
