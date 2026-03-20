from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="PR Assistant")
    app_env: Literal["development", "test", "production"] = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(default="info")
    github_webhook_secret: str = Field(default="")
    ai_provider: Literal["groq"] = Field(default="groq")
    ai_model: str = Field(default="")
    ai_timeout_seconds: float = Field(default=30.0, gt=0)
    groq_api_key: str = Field(default="")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")

    @model_validator(mode="after")
    def validate_production_defaults(self) -> "Settings":
        if self.app_env == "production" and self.log_level == "debug":
            raise ValueError("LOG_LEVEL=debug is not allowed when APP_ENV=production")

        if not self.github_webhook_secret:
            if self.app_env == "production":
                raise ValueError("GITHUB_WEBHOOK_SECRET is required when APP_ENV=production")
            self.github_webhook_secret = "dev-secret"

        if not self.ai_model:
            self.ai_model = "openai/gpt-oss-120b"

        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when AI_PROVIDER=groq")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings() -> Settings:
    try:
        return get_settings()
    except ValidationError:
        raise
