from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    OPENAI_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4.1-mini"
    PROMPT_VERSION: str = "phase1-extract-v1"
    TZ: str = "Asia/Tokyo"
    FOLLOWUP_MORNING: str = "09:00"
    FOLLOWUP_NOON: str = "13:00"
    FOLLOWUP_EVENING: str = "18:00"

    class Config:
        env_file = ".env"

settings = Settings()
