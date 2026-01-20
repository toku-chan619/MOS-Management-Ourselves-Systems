from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyUrl

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str

    # Secrets: 必須（デフォルトを置かない）
    OPENAI_API_KEY: str = Field(min_length=1)

    # これは秘密ではないのでデフォルト可
    LLM_MODEL: str = "gpt-4.1-mini"
    PROMPT_VERSION: str = "phase1-extract-v1"

    APP_BASE_URL: AnyUrl = "http://localhost:8000"

    TZ: str = "Asia/Tokyo"
    FOLLOWUP_MORNING: str = "09:00"
    FOLLOWUP_NOON: str = "13:00"
    FOLLOWUP_EVENING: str = "18:00"

    # Reminders & Notifications
    REMINDER_SCAN_INTERVAL_MIN: int = 10
    RENDER_BATCH_SIZE: int = 10

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
