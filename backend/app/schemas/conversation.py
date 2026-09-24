"""Conversation and message schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageRead(BaseModel):
    """Message representation returned to client."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    metadata_json: Optional[str] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Summary of a conversation for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    """Detailed view of a conversation including message history."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    """Payload to explicitly create a conversation."""
    title: Optional[str] = Field("New Conversation", max_length=255)
