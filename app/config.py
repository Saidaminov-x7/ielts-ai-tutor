from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: SecretStr | None = None
    owner_telegram_id: int | None = None
    openai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    webhook_base_url: str | None = None
    webhook_secret_token: SecretStr | None = None
    daily_job_secret: SecretStr | None = None
    daily_job_url: str | None = None
    port: int = Field(default=8080, ge=1, le=65535)
    openai_model: str = "gpt-4.1-mini"
    gemini_model: str = "gemini-3.8-flash"
    max_daily_gemini_requests: int = Field(default=10, ge=0, le=100)
    database_url: str = "sqlite:///./data/ielts.db"
    monthly_ai_budget_usd: float = Field(default=2.0, ge=0)
    ai_input_price_per_million: float = Field(default=0.4, ge=0)
    ai_output_price_per_million: float = Field(default=1.6, ge=0)
    max_daily_ai_requests: int = Field(default=3, ge=0)
    max_writing_chars: int = Field(default=5000, ge=200, le=20000)
    timezone: str = "Asia/Tashkent"
    reminder_time: str = "19:00"
    github_token: SecretStr | None = None
    github_repo: str | None = None
    github_branch: str = "main"
    github_notes_path: str = "IELTS Tutor"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
