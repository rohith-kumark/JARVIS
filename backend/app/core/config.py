"""Configuration settings for JARVIS AI Assistant."""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "JARVIS AI Assistant"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS settings
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM Settings
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-3.6-flash", description="Gemini model name")
    DEFAULT_LLM_PROVIDER: str = Field(default="gemini", description="LLM provider: gemini or mock")

    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./jarvis.db",
        description="SQLAlchemy database connection URL (defaults to SQLite, ready for PostgreSQL)",
    )

    # Persistent Memory Settings
    MEMORY_FILE_PATH: str = Field(
        default="data/memory.json",
        description="Path to local persistent JSON memory storage file",
    )

    # Voice Assistant Settings (Phase 3)
    VOICE_ENABLED: bool = Field(default=True, description="Enable real-time voice subsystem")
    VOICE_MODEL: str = Field(
        default="gemini-2.5-flash-native-audio-latest",
        description="Gemini model for real-time voice streaming",
    )
    VOICE_NAME: str = Field(
        default="Puck",
        description="Default Gemini voice name (e.g. Puck, Charon, Kore, Fenrir, Aoede)",
    )
    VOICE_INPUT_SAMPLE_RATE: int = Field(default=16000, description="Input PCM sample rate in Hz")
    VOICE_OUTPUT_SAMPLE_RATE: int = Field(default=24000, description="Output PCM sample rate in Hz")
    VOICE_CHANNELS: int = Field(default=1, description="Audio channel count (1 for mono)")

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


# Cached settings instance
_settings = None


def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
