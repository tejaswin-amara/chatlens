"""Lightweight document loader for academic documents, syllabi, notes, and schedules.

Parses .pdf, .txt, .md, .toml, and .json files under data/ into structured knowledge
records stored in SQLite knowledge_docs with [Doc: <filename>] citations.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import tomllib
import zlib
from pathlib import Path
from typing import Any

from src.utils.deduplication import deduplicator

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Pure-Python robust PDF text extractor without external dependencies.

    Extracts text from decompressed Flate streams, BT..ET text blocks, and Tj/TJ operators.
    Safely handles corrupt, encrypted, or empty PDFs without raising exceptions.
    """
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        return ""

    try:
        data = pdf_path.read_bytes()
    except Exception as e:
        logger.warning(f"Could not read PDF bytes from {pdf_path}: {e}")
        return ""

    text_parts: list[str] = []

    # 1. Search for stream ... endstream blocks and decompress FlateDecode
    stream_pattern = re.compile(b"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
    for match in stream_pattern.finditer(data):
        raw_stream = match.group(1)
        decompressed: bytes | None = None
        try:
            decompressed = zlib.decompress(raw_stream)
        except Exception:
            try:
                decompressed = zlib.decompress(raw_stream, -zlib.MAX_WBITS)
            except Exception:
                decompressed = raw_stream

        if decompressed:
            # Extract text from Tj/TJ operators: (Some text) Tj or [(Part1) 10 (Part2)] TJ
            # Tj pattern: \((.*?)\)\s*Tj
            tj_matches = re.findall(
                rb"\(((?:[^\)\\]|\\.)*)\)\s*T[jJ]", decompressed, flags=re.DOTALL
            )
            for tm in tj_matches:
                cleaned = re.sub(rb"\\([()\\])", rb"\1", tm)
                with contextlib.suppress(Exception):
                    s = cleaned.decode("utf-8", errors="ignore").strip()
                    if s and len(s) > 1:
                        text_parts.append(s)

            # TJ array pattern: \[(.*?)\]\s*TJ
            arr_matches = re.findall(rb"\[(.*?)\]\s*TJ", decompressed, flags=re.DOTALL)
            for am in arr_matches:
                sub_strings = re.findall(rb"\(((?:[^\)\\]|\\.)*)\)", am, flags=re.DOTALL)
                joined = "".join(
                    re.sub(rb"\\([()\\])", rb"\1", part).decode("utf-8", errors="ignore")
                    for part in sub_strings
                ).strip()
                if joined and len(joined) > 1:
                    text_parts.append(joined)

    # 2. Fallback: scan outer data for literal (text) Tj if stream search yielded very little
    if len(" ".join(text_parts).strip()) < 20:
        raw_tjs = re.findall(rb"\(((?:[^\)\\]|\\.)*)\)\s*T[jJ]", data, flags=re.DOTALL)
        for r_tm in raw_tjs:
            with contextlib.suppress(Exception):
                s = r_tm.decode("utf-8", errors="ignore").strip()
                if s and len(s) > 1:
                    text_parts.append(s)

    return " ".join(text_parts).strip()


def chunk_text(text: str, max_chunk_size: int = 750) -> list[str]:
    """Split text into coherent paragraphs/chunks."""
    clean = re.sub(r"\r\n|\r", "\n", text).strip()
    if not clean:
        return []

    paragraphs = re.split(r"\n\s*\n+", clean)
    chunks: list[str] = []
    current_buf: list[str] = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        if current_len + len(p_clean) > max_chunk_size and current_buf:
            chunks.append("\n\n".join(current_buf))
            current_buf = [p_clean]
            current_len = len(p_clean)
        else:
            current_buf.append(p_clean)
            current_len += len(p_clean)

    if current_buf:
        chunks.append("\n\n".join(current_buf))

    return chunks


class DocumentKnowledgeLoader:
    """Indexes academic documents into SQLite knowledge_docs."""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)

    def index_all(self) -> int:
        """Scan data_dir and index .pdf, .txt, .md, .toml, and .json documents."""
        if not self.data_dir.exists():
            return 0

        total_indexed = 0
        for file_path in self.data_dir.glob("**/*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            ext = file_path.suffix.lower()
            if ext in (".pdf", ".txt", ".md"):
                count = self.index_document_file(file_path)
                total_indexed += count
            elif ext == ".toml":
                count = self.index_toml_file(file_path)
                total_indexed += count
            elif ext == ".json" and file_path.name == "academic_intelligence.json":
                count = self.index_academic_intel(file_path)
                total_indexed += count

        logger.info(
            f"Document knowledge loader indexed {total_indexed} chunks from {self.data_dir}"
        )
        return total_indexed

    def index_document_file(self, file_path: Path) -> int:
        """Parse text/markdown or PDF and persist to knowledge_docs."""
        ext = file_path.suffix.lower()
        content = ""
        if ext == ".pdf":
            content = extract_text_from_pdf(file_path)
        else:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception as e:
                logger.warning(f"Failed to read text from {file_path}: {e}")
                return 0

        if not content:
            return 0

        chunks = chunk_text(content, max_chunk_size=750)
        filename = file_path.name
        source_tag = f"[Doc: {filename}]"

        for idx, chunk in enumerate(chunks):
            # Extract first sentence or title as heading
            first_line = chunk.split("\n")[0][:80].strip()
            deduplicator.store_knowledge_doc(
                filename=filename,
                chunk_index=idx,
                title=first_line,
                text=chunk,
                source=source_tag,
            )
        return len(chunks)

    def index_toml_file(self, file_path: Path) -> int:
        """Index calendar and timetable TOML schedules."""
        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            logger.debug(f"Could not parse TOML file {file_path}: {e}")
            return 0

        filename = file_path.name
        source_tag = f"[Doc: {filename}]"
        chunks: list[tuple[str, str]] = []

        # 1. Calendar milestones
        if "milestones" in data or "calendar" in data or "events" in data:
            events_dict = data.get("milestones") or data.get("calendar") or data.get("events") or {}
            for event_name, event_info in events_dict.items():
                m_title = event_name.replace("_", " ").title()
                if isinstance(event_info, dict):
                    desc = f"Academic Milestone: {m_title}\n"
                    desc += (
                        f"Dates: {event_info.get('start_date', '')} to "
                        f"{event_info.get('end_date', '')}\n"
                    )
                    desc += f"Description: {event_info.get('description', '')}"
                    chunks.append((event_name, desc))
                elif isinstance(event_info, str):
                    desc = f"Academic Milestone: {m_title}\nDate: {event_info}"
                    chunks.append((event_name, desc))

        # 2. Timetable slots
        if "slots" in data or "courses" in data:
            slots = data.get("slots", [])
            by_course: dict[str, list[dict[str, Any]]] = {}
            for s in slots:
                c_code = s.get("course_code") or s.get("code") or "Unknown"
                by_course.setdefault(c_code, []).append(s)

            for c_code, c_slots in by_course.items():
                c_name = c_slots[0].get("course_name") or c_code
                lines = [f"Course Timetable: {c_name} ({c_code})"]
                for slot in c_slots:
                    lines.append(
                        f"• {slot.get('day')}: Period {slot.get('period')} "
                        f"({slot.get('start_time')}–{slot.get('end_time')}) | "
                        f"Room: {slot.get('room')} | Faculty: {slot.get('faculty')}"
                    )
                chunks.append((c_name, "\n".join(lines)))

        for idx, (title, text) in enumerate(chunks):
            deduplicator.store_knowledge_doc(
                filename=filename,
                chunk_index=idx,
                title=title,
                text=text,
                source=source_tag,
            )
        return len(chunks)

    def index_academic_intel(self, file_path: Path) -> int:
        """Index exams, defences, and viva questions from academic_intelligence.json."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.debug(f"Could not parse JSON intel from {file_path}: {e}")
            return 0

        filename = file_path.name
        source_tag = f"[Doc: {filename}]"
        chunks: list[tuple[str, str]] = []

        for exam in data.get("exams", []):
            title = f"{exam.get('event')} - {exam.get('course')}"
            desc = (
                f"EXAM / DEFENCE SCHEDULE:\n"
                f"Course: {exam.get('course')} ({exam.get('course_code')})\n"
                f"Section: {exam.get('section')} Event: {exam.get('event')}\n"
                f"Date: {exam.get('date')} Time: {exam.get('time')}\n"
                f"Room: {exam.get('room')} Faculty: {exam.get('faculty')}\n"
                f"Lab Technician: {exam.get('lab_technician') or 'None'}"
            )
            chunks.append((title, desc))

        for exp in data.get("lab_experiments", []):
            title = f"Lab Experiment: {exp.get('title')}"
            viva_lines = "\n".join(f"  - Viva: {q}" for q in exp.get("viva_questions", []))
            desc = (
                f"LAB EXPERIMENT {exp.get('id')}: {exp.get('title')}\n"
                f"Task: {exp.get('task')}\n"
                f"Viva Questions & Answers:\n{viva_lines}"
            )
            chunks.append((title, desc))

        for idx, (title, text) in enumerate(chunks):
            deduplicator.store_knowledge_doc(
                filename=filename,
                chunk_index=idx,
                title=title,
                text=text,
                source=source_tag,
            )
        return len(chunks)


document_loader = DocumentKnowledgeLoader()
