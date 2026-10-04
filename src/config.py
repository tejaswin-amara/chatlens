"""Configuration settings loaded from environment variables using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")
    telegram_session_string: str = Field(default="", alias="TELEGRAM_SESSION_STRING")

    google_credentials_base64: str = Field(default="", alias="GOOGLE_CREDENTIALS_BASE64")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", alias="GEMINI_MODEL")

    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")
    google_sheet_id: str | None = Field(default=None, alias="GOOGLE_SHEET_ID")
    spark_mode: str = "dry"
    spark_chat_ids: str = ""
    spark_db: str = "spark.db"
    bot_token: str | None = Field(default=None, alias="BOT_TOKEN")
    owner_chat_id: int | None = Field(default=None, alias="OWNER_CHAT_ID")
    gemini_daily_budget: int = Field(default=50, alias="GEMINI_DAILY_BUDGET")
    spark_media: bool = Field(default=False, alias="SPARK_MEDIA")
    spark_timetable: str = Field(default="data/timetable_T04.toml", alias="SPARK_TIMETABLE")

    @property
    def allowed_chat_ids(self) -> list[int]:
        if not self.spark_chat_ids:
            return []
        ids = []
        for x in self.spark_chat_ids.replace(";", ",").split(","):
            if x.strip():
                try:
                    ids.append(int(x.strip()))
                except ValueError:
                    pass
        return ids
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def validate_required(self) -> None:
        missing: list[str] = []
        if not self.telegram_api_id:
            missing.append("TELEGRAM_API_ID")
        if not self.telegram_api_hash:
            missing.append("TELEGRAM_API_HASH")
        if not self.telegram_session_string:
            missing.append("TELEGRAM_SESSION_STRING")
        if not self.google_credentials_base64:
            missing.append("GOOGLE_CREDENTIALS_BASE64")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if self.spark_mode not in ("dry", "confirm", "live"):
            raise ValueError("SPARK_MODE must be dry, confirm, or live")
        if not self.allowed_chat_ids:
            raise ValueError("SPARK_CHAT_IDS cannot be empty")

        if self.spark_mode in ("confirm", "live"):
            if not self.bot_token:
                missing.append("BOT_TOKEN")
            if not self.owner_chat_id:
                missing.append("OWNER_CHAT_ID")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
