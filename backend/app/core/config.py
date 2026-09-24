from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration loaded from environment variables and .env file.
    Never hardcode secrets. All values can be overridden via environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application
    APP_NAME: str = "JARVIS AI Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Host to bind server")
    PORT: int = Field(default=8000, description="Port to bind server")
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key. If absent, fallback to mock provider for local development",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.6-flash",
        description="Default Gemini model to use for reasoning and tool orchestration",
    )
    DEFAULT_LLM_PROVIDER: str = Field(
        default="gemini",
        description="Default provider: 'gemini' or 'mock'",
    )

    # WebSocket & System
    WS_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=30, description="WebSocket ping/pong interval")
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
