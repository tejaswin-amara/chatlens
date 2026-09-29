"""Tier-2 Multimodal Gemini AI Extractor for unstructured text, voice, and circular media."""

from datetime import datetime

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an expert PA parsing university notices for student groups (S-10/S-11).\n"
    "Extract actionable academic events into the requested JSON schema.\n"
    "Identify:\n"
    "- Intent: ROOM_OVERRIDE, HOLIDAY, EXAM_DEADLINE, TASK, or UNKNOWN.\n"
    "- Course name: (e.g. DSA, OSSP, ML, ESD, DBSE, Japanese)\n"
    "- Course code: (e.g., 25CS2103E)\n"
    "- Room: (e.g. H-005, HC-15C, H-301A, H107A, H006)\n"
    "- Target date: (ISO YYYY-MM-DD format)\n"
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

    def _get_client(self) -> genai.Client:
        if not self._client:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_from_text(
        self, text: str, message_date: datetime | None = None
    ) -> ExtractedAcademicEvent:
        client = self._get_client()
        ref_date = (message_date or datetime.now()).strftime("%Y-%m-%d")
        prompt = f"Reference Today Date: {ref_date}\n\nAnnouncement Text:\n{text}"

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExtractedAcademicEvent,
                temperature=0.1,
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        return ExtractedAcademicEvent.model_validate_json(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_from_voice(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        message_date: datetime | None = None,
    ) -> ExtractedAcademicEvent:
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
                response_schema=ExtractedAcademicEvent,
                temperature=0.1,
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        return ExtractedAcademicEvent.model_validate_json(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_from_media(
        self,
        media_bytes: bytes,
        mime_type: str = "image/jpeg",
        message_date: datetime | None = None,
    ) -> ExtractedAcademicEvent:
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
                response_schema=ExtractedAcademicEvent,
                temperature=0.1,
            ),
        )

        if response.parsed and isinstance(response.parsed, ExtractedAcademicEvent):
            return response.parsed

        return ExtractedAcademicEvent.model_validate_json(response.text)


ai_extractor = AIExtractor()
