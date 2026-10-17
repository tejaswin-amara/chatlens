"""ChatLens configuration — loads settings from .env file."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_API_ID: str | None = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH: str | None = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_STRING: str | None = os.getenv("TELEGRAM_SESSION_STRING")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))
