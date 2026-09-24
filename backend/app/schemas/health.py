from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(default="ok", description="Overall system health status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment (development, production)")
    llm_provider: str = Field(description="Currently active LLM provider")
    tools_registered_count: int = Field(description="Total number of tools loaded in registry")
    database_status: str = Field(default="ready", description="PostgreSQL connection status")
    vector_store_status: str = Field(default="ready", description="Vector database engine status")
    vector_documents_count: int = Field(default=0, description="Total indexed vectors in vector store")
    uptime_seconds: float = Field(description="System uptime in seconds")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
