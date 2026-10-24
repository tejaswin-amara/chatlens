"""Configuration settings loaded from environment variables using Pydantic Settings."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: SecretStr = Field(default=SecretStr(""), alias="TELEGRAM_API_HASH")
    telegram_session_string: SecretStr = Field(
        default=SecretStr(""), alias="TELEGRAM_SESSION_STRING"
    )

    google_credentials_base64: SecretStr = Field(
        default=SecretStr(""), alias="GOOGLE_CREDENTIALS_BASE64"
    )

    gemini_api_key: SecretStr = Field(default=SecretStr(""), alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", alias="GEMINI_MODEL")

    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")
    google_sheet_id: str | None = Field(default=None, alias="GOOGLE_SHEET_ID")
    spark_mode: Literal["dry", "confirm", "live"] = Field(default="dry", alias="SPARK_MODE")
    spark_chat_ids: str = Field(default="", alias="SPARK_CHAT_IDS")
    spark_db: str = Field(default="spark.db", alias="SPARK_DB")
    bot_token: SecretStr | None = Field(default=None, alias="BOT_TOKEN")
    owner_chat_id: int | None = Field(default=None, alias="OWNER_CHAT_ID")
    gemini_daily_budget: int = Field(default=50, alias="GEMINI_DAILY_BUDGET")
    spark_media: bool = Field(default=False, alias="SPARK_MEDIA")
    spark_timetable: str = Field(default="data/timetable_T04.toml", alias="SPARK_TIMETABLE")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    erp_username: str = Field(default="2520090104", alias="ERP_USERNAME")
    erp_password: SecretStr = Field(default=SecretStr(""), alias="ERP_PASSWORD")
    telegram_user_rate_limit_rps: float = Field(
        default=1.0, alias="TELEGRAM_USER_RATE_LIMIT_RPS"
    )
    telegram_group_rate_limit_rpm: float = Field(
        default=20.0, alias="TELEGRAM_GROUP_RATE_LIMIT_RPM"
    )
    telegram_global_rate_limit_rps: float = Field(
        default=25.0, alias="TELEGRAM_GLOBAL_RATE_LIMIT_RPS"
    )
    circuit_breaker_error_threshold: int = Field(
        default=3, alias="CIRCUIT_BREAKER_ERROR_THRESHOLD"
    )
    circuit_breaker_cooldown_seconds: int = Field(
        default=300, alias="CIRCUIT_BREAKER_COOLDOWN_SECONDS"
    )
    startup_debounce_seconds: int = Field(default=900, alias="STARTUP_DEBOUNCE_SECONDS")

    @property
    def allowed_chat_ids(self) -> list[int]:
        if not self.spark_chat_ids:
            return []
        ids = []
        for x in self.spark_chat_ids.replace(";", ",").split(","):
            token = x.strip()
            if token:
                try:
                    ids.append(int(token))
                except ValueError as err:
                    raise ValueError(f"Invalid non-integer chat id: {token}") from err
        return ids

    def validate_required(self) -> None:
        missing: list[str] = []
        if not self.telegram_api_id:
            missing.append("TELEGRAM_API_ID")
        if not self.telegram_api_hash.get_secret_value():
            missing.append("TELEGRAM_API_HASH")
        if not self.telegram_session_string.get_secret_value():
            missing.append("TELEGRAM_SESSION_STRING")
        if not self.google_credentials_base64.get_secret_value():
            missing.append("GOOGLE_CREDENTIALS_BASE64")
        if not self.gemini_api_key.get_secret_value():
            missing.append("GEMINI_API_KEY")
        if self.spark_mode not in ("dry", "confirm", "live"):
            raise ValueError("SPARK_MODE must be dry, confirm, or live")
        if not self.allowed_chat_ids:
            raise ValueError("SPARK_CHAT_IDS cannot be empty")

        if self.spark_mode in ("confirm", "live"):
            if not self.bot_token or not self.bot_token.get_secret_value():
                missing.append("BOT_TOKEN")
            if not self.owner_chat_id:
                missing.append("OWNER_CHAT_ID")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
