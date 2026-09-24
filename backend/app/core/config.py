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

    # Database (PostgreSQL) Configuration
    POSTGRES_SERVER: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="jarvis", description="PostgreSQL database name")
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Full database URL override. If omitted, constructed from POSTGRES_* settings.",
    )

    # Vector Database Configuration (Open-Source Local Persistent / ChromaDB)
    VECTOR_STORE_PATH: str = Field(
        default="backend/data/vector_store",
        description="Filesystem path for persistent vector store storage",
    )
    VECTOR_STORE_TYPE: str = Field(
        default="embedded",
        description="Vector store engine type: 'embedded' or 'chroma'",
    )

    # WebSocket & System
    WS_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=30, description="WebSocket ping/pong interval")
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")

    @property
    def async_database_url(self) -> str:
        """Returns the asyncpg connection string for SQLAlchemy 2.0."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
