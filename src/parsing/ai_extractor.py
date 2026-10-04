"""Tier-2 Multimodal Gemini AI Extractor for unstructured text, voice, and circular media."""

import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import settings
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an expert PA parsing university notices for student groups (S-10/S-11).\n"
    "Extract actionable academic events into the requested JSON schema.\n"
    "Identify:\n"
    "- Intent: ROOM_OVERRIDE, HOLIDAY, CLASS_CANCELLED, EXAM_DEADLINE, TASK, or UNKNOWN.\n"
    "- Course name and code: use exactly one of DSA=25CS2103E, OSSP=25CS2104E, ML=25SC2107E, ESD=25EC2206E, DBSE=25CS1302E, JAPANESE=25FL2112E; null if none.\n"
    "- Room: (e.g. H-005, HC-15C, H-301A, H107A, H006)\n"
    "- Target date: (ISO YYYY-MM-DD format). Resolve relative dates against the IST reference date.\n"
    "- Period: (e.g. P3-P4, Period 1, 10:00 AM - 11:40 AM)\n"
    "- Summary: Concise recap.\n"
    "- Action Required: True if a task/deadline needs fulfillment."
)

class AIExtractor:
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self._client: genai.Client | None = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_budget (
                    day TEXT PRIMARY KEY,
                    calls INTEGER
                )
            """)

    def _check_budget(self) -> bool:
        IST = ZoneInfo("Asia/Kolkata")
        today = datetime.now(IST).strftime("%Y-%m-%d")
        with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
            cursor = conn.execute("SELECT calls FROM llm_budget WHERE day = ?", (today,))
            row = cursor.fetchone()
            if row and row[0] >= settings.gemini_daily_budget:
                return False
            conn.execute(
                "INSERT INTO llm_budget (day, calls) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET calls = calls + 1",
                (today,)
            )
        return True

    def _redact_pii(self, text: str) -> str:
        # Redact phone numbers, emails and URLs
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        text = re.sub(r'https?://\S+', '[URL]', text)
        # Redact phones: simple regex
        text = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[PHONE]', text)
        return text


    def _get_client(self) -> genai.Client:
        if not self._client:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, errors.ClientError))
    )
    def extract_from_text(
        self, text: str, message_date: datetime | None = None
    ) -> ExtractedAcademicEvent | None:
        if not self._check_budget():
            logger.warning("LLM daily budget exhausted. Skipping extraction.")
            return None

        client = self._get_client()
        ref_date = (message_date or datetime.now()).strftime("%Y-%m-%d")
        safe_text = self._redact_pii(text)
        prompt = f"Reference Today Date: {ref_date}\n\nAnnouncement Text:\n{safe_text}"

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExtractedAcademicEvent
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        if not response.text:
            return None
        try:
            return ExtractedAcademicEvent.model_validate_json(response.text)
        except Exception:
            return None


    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, errors.ClientError))
    )
    def extract_from_voice(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        message_date: datetime | None = None,
    ) -> ExtractedAcademicEvent | None:
        if not settings.spark_media:
            return None
        if not self._check_budget():
            logger.warning("LLM daily budget exhausted. Skipping extraction.")
            return None

        client = self._get_client()
        ref_date = (message_date or datetime.now()).strftime("%Y-%m-%d")
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            f"Reference Today Date: {ref_date}\n"
            "Transcribe this voice note and extract the academic event/task."
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=[audio_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExtractedAcademicEvent
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        if not response.text:
            return None
        try:
            return ExtractedAcademicEvent.model_validate_json(response.text)
        except Exception:
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, errors.ClientError))
    )
    def extract_from_media(
        self,
        media_bytes: bytes,
        mime_type: str = "image/jpeg",
        message_date: datetime | None = None,
    ) -> ExtractedAcademicEvent | None:
        if not settings.spark_media:
            return None
        if not self._check_budget():
            logger.warning("LLM daily budget exhausted. Skipping extraction.")
            return None

        client = self._get_client()
        ref_date = (message_date or datetime.now()).strftime("%Y-%m-%d")
        media_part = types.Part.from_bytes(data=media_bytes, mime_type=mime_type)
        prompt = (
            f"Reference Today Date: {ref_date}\n"
            "Perform OCR on this notice and extract the academic event or timetable change."
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=[media_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExtractedAcademicEvent
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        if not response.text:
            return None
        try:
            return ExtractedAcademicEvent.model_validate_json(response.text)
        except Exception:
            return None


ai_extractor = AIExtractor()
