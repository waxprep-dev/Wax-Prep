from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):

    # App
    app_env: str = Field(default="development", env="APP_ENV")
    app_name: str = Field(default="WaxPrep", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_secret_key: str = Field(env="APP_SECRET_KEY")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    port: int = Field(default=8000, env="PORT")

    # Render deployment URL
    app_url: str = Field(default="", env="APP_URL")

    # WhatsApp Business API
    whatsapp_access_token: str = Field(env="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(env="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_business_account_id: str = Field(env="WHATSAPP_BUSINESS_ACCOUNT_ID")
    whatsapp_verify_token: str = Field(env="WHATSAPP_VERIFY_TOKEN")
    whatsapp_app_secret: str = Field(env="WHATSAPP_APP_SECRET")

    # Telegram
    telegram_bot_token: str = Field(env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(env="TELEGRAM_WEBHOOK_SECRET")

    # Supabase
    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_key: str = Field(env="SUPABASE_KEY")
    supabase_service_key: str = Field(env="SUPABASE_SERVICE_KEY")

    # Groq (Primary AI) — Multiple keys for rotation
    groq_api_key: str = Field(env="GROQ_API_KEY")
    groq_api_key_2: Optional[str] = Field(default=None, env="GROQ_API_KEY_2")
    groq_api_key_3: Optional[str] = Field(default=None, env="GROQ_API_KEY_3")
    groq_api_key_4: Optional[str] = Field(default=None, env="GROQ_API_KEY_4")
    groq_api_key_5: Optional[str] = Field(default=None, env="GROQ_API_KEY_5")
    groq_primary_model: str = Field(default="llama-3.3-70b-versatile", env="GROQ_PRIMARY_MODEL")
    groq_fast_model: str = Field(default="llama-3.1-8b-instant", env="GROQ_FAST_MODEL")
    groq_max_tokens: int = Field(default=1024, env="GROQ_MAX_TOKENS")
    groq_temperature: float = Field(default=0.7, env="GROQ_TEMPERATURE")

    @property
    def groq_api_keys(self) -> List[str]:
        keys = [self.groq_api_key]
        if self.groq_api_key_2:
            keys.append(self.groq_api_key_2)
        if self.groq_api_key_3:
            keys.append(self.groq_api_key_3)
        if self.groq_api_key_4:
            keys.append(self.groq_api_key_4)
        if self.groq_api_key_5:
            keys.append(self.groq_api_key_5)
        return keys

    # Gemini (Secondary AI)
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Sentry (Error Monitoring)
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # System Configuration
    message_dedup_window_seconds: int = Field(default=60, env="MESSAGE_DEDUP_WINDOW_SECONDS")
    max_messages_per_minute_per_user: int = Field(default=10, env="MAX_MESSAGES_PER_MINUTE_PER_USER")
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    memory_compression_threshold: int = Field(default=50, env="MEMORY_COMPRESSION_THRESHOLD")
    spaced_rep_default_interval_days: int = Field(default=3, env="SPACED_REP_DEFAULT_INTERVAL_DAYS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
