"""Memory schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MemoryItem(BaseModel):
    """A memory item representing context or saved knowledge."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: Optional[str] = None
    key: str
    value: str
    memory_type: str
    created_at: datetime


class MemoryResponse(BaseModel):
    """Response returned by GET /api/memory."""
    conversation_id: Optional[str] = None
    memories: List[MemoryItem] = Field(default_factory=list)
    preferences: Dict[str, str] = Field(default_factory=dict)
