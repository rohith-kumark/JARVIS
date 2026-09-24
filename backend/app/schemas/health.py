"""Health check schemas."""

from typing import List
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Payload returned by GET /api/health."""
    status: str
    app_name: str
    version: str
    environment: str
    database: str
    llm_provider: str
    model: str
    tools_count: int
    registered_tools: List[str]
