from pydantic_settings import BaseSettings
from functools import lru_cache
import os

_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:5199"]
    firebase_credentials_path: str = "serviceAccountKey.json"
    github_token: str = ""
    webhook_secret: str = "hapura-secret-change-me"
    openclaw_webhook_url: str = ""
    gcp_project_id: str = "trendkr-hapura"
    gcp_region: str = "asia-southeast1"
    integrations_cache_ttl_minutes: int = 15
    # AI agents
    openai_api_key: str = ""
    openai_base_url: str = "https://vertex-key.com/api/v1"
    llm_model: str = "omega/claude-sonnet-4-6"
    model_health_checker: str = "lite/claude-haiku-4-5"
    model_bug_detective: str = "omega/claude-sonnet-4-6"
    model_strategist: str = "omega/claude-sonnet-4-6"
    model_revenue_forecaster: str = "omega/claude-opus-4-6"
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
