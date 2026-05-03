from pydantic_settings import BaseSettings
from functools import lru_cache
import os

_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: list[str] = [
        "http://localhost:5199",
        "https://hapura-hq.web.app",
        "https://hq.hapura.vn",
    ]
    firebase_credentials_path: str = "serviceAccountKey.json"
    github_token: str = ""
    webhook_secret: str = "hapura-secret-change-me"
    scheduler_secret: str = "hapura-scheduler-secret-change-me"
    openclaw_webhook_url: str = ""
    gcp_project_id: str = "trendkr-hapura"
    gcp_region: str = "asia-southeast1"
    integrations_cache_ttl_minutes: int = 15
    # AI agents
    openai_api_key: str = ""
    openai_base_url: str = "https://vertex-key.com/api/v1"
    llm_model: str = "openai/aws/claude-sonnet-4-6"
    model_health_checker: str = "openai/aws/claude-haiku-4-5"
    model_bug_detective: str = "openai/aws/claude-sonnet-4-6"
    model_strategist: str = "openai/aws/claude-sonnet-4-6"
    model_revenue_forecaster: str = "openai/aws/claude-opus-4-6"
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = "aria-webhook-secret-change-me"
    model_aria: str = "openai/aws/claude-sonnet-4-6"
    # Workspace agents
    model_director: str = "openai/aws/claude-opus-4-6"
    model_aso_analyst: str = "openai/aws/claude-sonnet-4-6"
    model_content_strategist: str = "openai/aws/claude-sonnet-4-6"
    model_competitor_watcher: str = "openai/aws/claude-sonnet-4-6"
    # Auto-social module
    buffer_api_key: str = ""
    buffer_graphql_url: str = "https://api.buffer.com"
    auto_social_admin_uids: str = ""
    auto_social_default_channel_id: str = "69f5bb6f5c4c051afa015f6d"
    gcs_assets_bucket: str = "hapura-hq-tiktok-assets"

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
