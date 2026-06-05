"""Configuration via pydantic-settings. Reads from .env automatically."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required
    SECRET_KEY: str = "dev-only-do-not-use-in-prod"

    # Optional / lazy-required
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    GEMINI_API_KEY: str = ""

    # Defaults
    TIMEZONE: str = "America/Los_Angeles"
    DB_URL: str = "sqlite+aiosqlite:///./data/coach.db"

    @property
    def async_db_url(self) -> str:
        # Render injects postgresql://, SQLAlchemy needs postgresql+asyncpg://
        if self.DB_URL.startswith("postgresql://"):
            return self.DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DB_URL
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    MORNING_NUDGE_HOUR: int = 7
    MORNING_NUDGE_MINUTE: int = 0
    EVENING_CHECKIN_HOUR: int = 21
    EVENING_CHECKIN_MINUTE: int = 0
    SUNDAY_PLAN_HOUR: int = 19
    SUNDAY_PLAN_MINUTE: int = 0

    DISABLE_BOT: bool = True       # default off until token is configured
    DISABLE_SCHEDULER: bool = True

    @property
    def bot_enabled(self) -> bool:
        return not self.DISABLE_BOT and bool(self.TELEGRAM_BOT_TOKEN)

    @property
    def scheduler_enabled(self) -> bool:
        return not self.DISABLE_SCHEDULER


settings = Settings()
