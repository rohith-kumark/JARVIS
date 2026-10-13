"""Data models for JARVIS Persistent Long-Term Memory."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class MemoryCategory(str, Enum):
    """Permitted memory categories."""
    PREFERENCE = "preference"
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    PROJECT = "project"
    LEARNING = "learning"
    WORKFLOW = "workflow"
    TECHNICAL = "technical"
    GOAL = "goal"
    OTHER = "other"

    @classmethod
    def from_string(cls, val: str) -> "MemoryCategory":
        """Normalize string to category enum or fallback to OTHER."""
        if not val:
            return cls.OTHER
        cleaned = val.strip().lower()
        for cat in cls:
            if cat.value == cleaned:
                return cat
        return cls.OTHER


def utcnow_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class MemoryRecord(BaseModel):
    """Schema representing an individual stored persistent memory."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., description="Durable memory statement about the user")
    category: str = Field(default="other", description="Category classification")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance weight between 0.0 and 1.0")
    source: str = Field(default="conversation", description="Origin of memory: conversation, manual, explicit")
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    last_accessed_at: Optional[str] = None
    access_count: int = 0


class MemoryCreate(BaseModel):
    """Payload for manually adding a memory."""
    content: str = Field(..., min_length=1, max_length=2000)
    category: Optional[str] = Field("other")
    importance: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    source: Optional[str] = Field("manual")


class MemoryUpdate(BaseModel):
    """Payload for updating an existing memory."""
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemorySearchRequest(BaseModel):
    """Payload for querying memories."""
    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=50)


class MemoryExtractionItem(BaseModel):
    """Individual memory extracted from a conversation turn."""
    content: str = Field(..., description="Fact or preference to remember")
    category: str = Field(default="other", description="Category of memory")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Significance score 0.0 to 1.0")


class MemoryExtractionResponse(BaseModel):
    """Model output validation schema for automatic memory extraction."""
    should_store: bool = False
    memories: List[MemoryExtractionItem] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    """Response containing list of stored memories."""
    memories: List[MemoryRecord] = Field(default_factory=list)
    total: int = 0
    preferences: dict = Field(default_factory=dict)
