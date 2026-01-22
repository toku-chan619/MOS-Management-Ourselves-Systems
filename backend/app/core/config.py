from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyUrl

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str

    # Secrets: 必須（デフォルトを置かない）
    OPENAI_API_KEY: str = Field(default="", min_length=0)  # Optional when using CLI backends

    # LLM Configuration
    LLM_BACKEND: str = "openai_api"  # openai_api, claude_cli, ollama_cli
    LLM_MODEL: str = "gpt-4o-mini"
    PROMPT_VERSION: str = "phase1-extract-v1"

    # CLI Backend Configuration (for claude_cli, ollama_cli)
    CLAUDE_CLI_PATH: str = "claude"
    OLLAMA_CLI_PATH: str = "ollama"
    OLLAMA_MODEL: str = "llama2"

    APP_BASE_URL: AnyUrl = "http://localhost:8000"

    TZ: str = "Asia/Tokyo"
    FOLLOWUP_MORNING: str = "09:00"
    FOLLOWUP_NOON: str = "13:00"
    FOLLOWUP_EVENING: str = "18:00"

    # Reminders & Notifications
    REMINDER_SCAN_INTERVAL_MIN: int = 10
    RENDER_BATCH_SIZE: int = 10

    # External Notification Providers
    LINE_NOTIFY_TOKEN: str = ""
    SLACK_WEBHOOK_URL: str = ""
    DISCORD_WEBHOOK_URL: str = ""

    # Webhook Verification
    LINE_CHANNEL_SECRET: str = ""
    SLACK_SIGNING_SECRET: str = ""

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
