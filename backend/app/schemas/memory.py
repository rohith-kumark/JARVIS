"""Memory schemas for Phase 1 and Phase 2."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.memory.models import (
    MemoryCategory,
    MemoryCreate,
    MemoryListResponse,
    MemoryRecord,
    MemorySearchRequest,
    MemoryUpdate,
)


class MemoryItem(BaseModel):
    """Legacy Phase 1 memory item representation."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: Optional[str] = None
    key: str
    value: str
    memory_type: str
    created_at: datetime


class MemoryResponse(BaseModel):
    """Response returned by legacy GET /api/memory."""
    conversation_id: Optional[str] = None
    memories: List[MemoryRecord] = Field(default_factory=list)
    total: int = 0
    preferences: Dict[str, str] = Field(default_factory=dict)


__all__ = [
    "MemoryRecord",
    "MemoryCreate",
    "MemoryUpdate",
    "MemorySearchRequest",
    "MemoryListResponse",
    "MemoryCategory",
    "MemoryItem",
    "MemoryResponse",
]
