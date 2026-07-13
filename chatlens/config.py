"""ChatLens configuration — loads settings from .env file."""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_API_ID: str | None = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH: str | None = os.getenv("TELEGRAM_API_HASH")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
DB_PATH: str = os.getenv("DB_PATH", "chatlens.db")
